# Implementation plan

1. **Docker Compose & Profiles Setup**:
   Add `vpn-proxy-alpha` and `vpn-proxy-beta` services to `backend/docker-compose.yaml` using `qmcgaw/gluetun:v3` under `profiles: ["vpn"]`. Configure OpenVPN credentials (`OPENVPN_USER`, `OPENVPN_PASSWORD`), US server regions, HTTP proxy on port 8888, and internal Docker firewall rules (`FIREWALL_OUTBOUND_SUBNETS`). Document environment variables in `docs/agents/CONFIGURATION.md`.

2. **Configuration Models**:
   Add `CAMPLY_PROXY_ENABLED` (default `False`), `CAMPLY_PROXY_URLS`, `CAMPLY_PROXY_CONTROL_URLS`, `CAMPLY_VPN_ROTATION_INTERVAL_MINUTES` (default `30`), `CAMPLY_VPN_MAX_REQUESTS_PER_IP` (default `1000`), and `CAMPLY_VPN_STRICT` (default `True`) to `backend/packages/worker/worker/config.py` and `backend/packages/backend/backend/config.py`.

3. **Proxy Manager & BaseProvider Transport Refactor**:
   Implement `ProxyManager` in `backend/packages/providers/providers/proxy.py` to maintain Valkey-backed state for active proxy index, request counts, and Gluetun control API client (`http://vpn-proxy:8000/v1/...`). Refactor `RetryTransport` and `BaseProvider` in `backend/packages/providers/providers/base.py` to route through the active proxy when enabled, while preserving completely unproxied direct connections by default. When `CAMPLY_VPN_STRICT=True`, proxy connection failures raise `ProxyUnavailableError` rather than falling back to direct connections.

4. **Zero-Downtime Background Rotation**:
   Implement Celery task `camply.vpn.rotate_pool` in `worker/tasks/`. The task connects to the standby Gluetun control port (`PUT /v1/vpn/status`), triggers reconnection, verifies the new public IP (`GET /v1/publicip/ip`), checks US geolocation, and atomically updates the active proxy key in Valkey (`vpn:proxy:active`). The previous active proxy drains gracefully and becomes the standby.

5. **Scheduler & Reactive Failover**:
   Register `camply.vpn.rotate_pool` in Celery Beat to evaluate time and request-volume thresholds. In `RetryTransport._execute_attempt`, intercept HTTP 429 and 403 responses, mark the current proxy as tainted, trigger immediate failover to the standby proxy, and retry the request.

6. **Admin Operations API & UI**:
   Add `GET /api/admin/operations/vpn/status` and `POST /api/admin/operations/vpn/rotate` to FastAPI admin routes. Register Prometheus metrics `camply_vpn_proxy_requests_total`, `camply_vpn_rotations_total`, and `camply_vpn_current_ip_info`. Add an egress VPN status card and manual rotation button to the frontend Admin Operations page.

7. **Verification & Quality Gates**:
   Write synthetic unit tests for `ProxyManager`, `RetryTransport` proxy injection, and strict kill-switch behavior. Verify full regression test suite passes with `CAMPLY_PROXY_ENABLED=false` and run Task quality gates (`task lint`, `task check`, `task test`).

## Constitution check

- **Default Off & Simplicity**: Zero changes to baseline network routing or runtime overhead when `CAMPLY_PROXY_ENABLED=false`. Standard developer setups do not require VPN credentials or containers.
- **Surgical Changes**: Internal microservice traffic (PostgreSQL, Valkey, Prometheus) remains strictly isolated from the VPN tunnel on the local Docker network.
- **Zero-Downtime Reliability**: Dual-proxy active/standby rotation prevents OpenVPN's 15–20s connection blackout from dropping in-flight scans.
- **Testing Integrity**: Tests use synthetic HTTP transports and mocked proxy servers; no live VPN subscriptions or credentials are required in CI.
