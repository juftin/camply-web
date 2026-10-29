# Implementation plan

1. **Docker Compose & Volume Setup for Multi-Config**:
   Add `vpn-proxy-alpha` and `vpn-proxy-beta` services to `backend/docker-compose.yaml` using `qmcgaw/gluetun:v3` under `profiles: ["vpn"]`. Configure OpenVPN credentials (`OPENVPN_USER`, `OPENVPN_PASSWORD`), US server regions, HTTP proxy on port 8888, and internal Docker firewall rules (`FIREWALL_OUTBOUND_SUBNETS`). Add volume mounts for `./vpn-configs:/gluetun/configs:ro` and shared active configuration volume `vpn_active_configs`. Document environment variables in `docs/agents/CONFIGURATION.md`.

2. **Configuration Models**:
   Add `CAMPLY_PROXY_ENABLED` (default `False`), `CAMPLY_PROXY_URLS`, `CAMPLY_PROXY_CONTROL_URLS`, `CAMPLY_VPN_SERVER_POOL` (list of server IDs), `CAMPLY_VPN_SERVER_POOL_FILE`, `CAMPLY_VPN_CONFIG_DIR`, `CAMPLY_VPN_SELECTION_STRATEGY` (default `"round_robin"`), `CAMPLY_VPN_COOLDOWN_HOURS` (default `2.0`), `CAMPLY_VPN_ROTATION_INTERVAL_MINUTES` (default `30`), `CAMPLY_VPN_MAX_REQUESTS_PER_IP` (default `1000`), and `CAMPLY_VPN_STRICT` (default `True`) to `backend/packages/worker/worker/config.py` and `backend/packages/backend/backend/config.py`.

3. **Server Inventory & Proxy Manager**:
   Implement `ProxyManager` in `backend/packages/providers/providers/proxy.py` to manage the pool of 1–100 configurations in Valkey:
   - Discover inventory from `CAMPLY_VPN_SERVER_POOL` or files in `CAMPLY_VPN_CONFIG_DIR`.
   - Maintain active servers, cooldown sorted set with expiration TTLs, and selection strategies (`round_robin`, `lru`, `random`).
   - Implement dynamic reconfiguration via Gluetun REST control client (`PUT /v1/openvpn/settings`) or symlink updates for custom configs.
   - Refactor `RetryTransport` and `BaseProvider` in `backend/packages/providers/providers/base.py` to route through the active proxy when enabled, while preserving completely unproxied direct connections by default. When `CAMPLY_VPN_STRICT=True`, proxy connection failures raise `ProxyUnavailableError` rather than falling back to direct connections.

4. **Zero-Downtime Background Rotation**:
   Implement Celery task `camply.vpn.rotate_pool` in `worker/tasks/`. The task queries the next clean, eligible server from the inventory, commands the standby Gluetun container to reconfigure and reconnect, verifies the new public IP and US geolocation (`GET /v1/publicip/ip`), and atomically updates the active proxy key and active server identifier in Valkey (`vpn:proxy:active`). The previous active proxy drains gracefully and becomes the standby.

5. **Scheduler & Reactive Cooldown Handling**:
   Register `camply.vpn.rotate_pool` in Celery Beat to evaluate time and request-volume thresholds. In `RetryTransport._execute_attempt`, intercept HTTP 429 and 403 responses, place the offending server in `vpn:servers:cooldown`, immediately trigger failover to the standby proxy using a clean server from the pool, and retry the request.

6. **Admin Operations API & Server Pool Inspector**:
   Add `GET /api/admin/operations/vpn/status` (including server pool stats and server table) and `POST /api/admin/operations/vpn/rotate` to FastAPI admin routes. Add `POST /api/admin/operations/vpn/cooldown/clear` to remove servers from cooldown. Register Prometheus metrics for proxied requests, rotations, configured servers, and cooled-down servers. Add an egress VPN status card, server pool table, and manual rotation actions to the frontend Admin Operations page.

7. **Verification & Quality Gates**:
   Write synthetic unit tests for server pool parsing (1–100 items), round-robin/LRU selection, cooldown mechanics, `ProxyManager`, and `RetryTransport` proxy injection. Verify full regression test suite passes with `CAMPLY_PROXY_ENABLED=false` and run Task quality gates (`task lint`, `task check`, `task test`).

## Constitution check

- **Default Off & Simplicity**: Zero changes to baseline network routing or runtime overhead when `CAMPLY_PROXY_ENABLED=false`. Standard developer setups do not require VPN credentials, containers, or config files.
- **Surgical Changes**: Internal microservice traffic (PostgreSQL, Valkey, Prometheus) remains strictly isolated from the VPN tunnel on the local Docker network.
- **Zero-Downtime Reliability & Scale**: Dual-proxy active/standby rotation prevents OpenVPN's 15–20s connection blackout from dropping in-flight scans while scaling seamlessly across 1 to 100 distinct VPN configurations.
- **Testing Integrity**: Tests use synthetic HTTP transports and mocked proxy servers; no live VPN subscriptions, credentials, or remote servers are required in CI.
