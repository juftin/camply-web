# Tasks: Worker VPN and proxy rotation for provider requests

## Phase 1: Infrastructure & Environment Configuration
- [ ] T1.1 Add Gluetun dual-proxy services (`vpn-proxy-alpha`, `vpn-proxy-beta`) to `backend/docker-compose.yaml` under `profiles: ["vpn"]` with OpenVPN configuration and volume mounts for `./vpn-configs`.
- [ ] T1.2 Add proxy and multi-server configuration fields to `backend/packages/worker/worker/config.py` and `backend/packages/backend/backend/config.py` (`CAMPLY_PROXY_ENABLED`, `CAMPLY_VPN_SERVER_POOL`, `CAMPLY_VPN_CONFIG_DIR`, `CAMPLY_VPN_SELECTION_STRATEGY`, `CAMPLY_VPN_COOLDOWN_HOURS`, `CAMPLY_VPN_STRICT`).
- [ ] T1.3 Document OpenVPN credentials, server pool syntax, and custom config directory layout in `docs/agents/CONFIGURATION.md`.

## Phase 2: Server Inventory & Proxy Transport
- [ ] T2.1 Implement server pool inventory discovery (parsing list, file, or 1–100 `.ovpn` files) and selection algorithms (`round_robin`, `lru`, `random`) in `backend/packages/providers/providers/proxy.py`.
- [ ] T2.2 Implement Valkey-backed state management for active servers, cooldown TTLs, and Gluetun dynamic reconfiguration client (`:8000`).
- [ ] T2.3 Refactor `RetryTransport` and `BaseProvider` in `backend/packages/providers/providers/base.py` to route through active proxy when enabled, and enforce strict kill-switch behavior (`ProxyUnavailableError`).
- [ ] T2.4 Add unit tests in `backend/packages/providers/tests/test_proxy.py` for server pool parsing (1–100 items), cooldown logic, round-robin rotation, direct connection defaults, and strict kill-switch error handling.

## Phase 3: Zero-Downtime Celery Rotation
- [ ] T3.1 Implement `camply.vpn.rotate_pool` Celery task in `backend/packages/worker/worker/tasks/` for background standby reconfiguration, verification, and atomic Valkey pointer swap.
- [ ] T3.2 Schedule `camply.vpn.rotate_pool` in Celery Beat with configurable interval and volume thresholds.
- [ ] T3.3 Implement reactive failover in `RetryTransport`: on HTTP 429 or 403, mark offending server in cooldown, trigger immediate failover to a clean server on the standby proxy, and retry.
- [ ] T3.4 Add unit tests for Celery rotation task execution, server deduplication between Alpha and Beta, and standby IP verification.

## Phase 4: Observability & Admin Operations UI
- [ ] T4.1 Register Prometheus metrics for proxied requests, rotations, configured server count, and cooled-down server count.
- [ ] T4.2 Add FastAPI endpoints `GET /api/admin/operations/vpn/status`, `POST /api/admin/operations/vpn/rotate`, and `POST /api/admin/operations/vpn/cooldown/clear` in `backend/packages/backend/backend/routers/admin.py`.
- [ ] T4.3 Add VPN Status card, Server Pool table (showing 1–100 servers and cooldown states), and manual rotation actions to frontend Admin Operations page (`AdminOperations.tsx`).
- [ ] T4.4 Add frontend component and API integration tests for VPN admin controls and server pool inspector.

## Phase 5: Verification & Quality Gates
- [ ] T5.1 Verify complete test suite passes without VPN containers running (`CAMPLY_PROXY_ENABLED=false`).
- [ ] T5.2 Verify synthetic proxy routing, multi-server cycling, and kill-switch enforcement when `CAMPLY_PROXY_ENABLED=true`.
- [ ] T5.3 Update `docs/agents/CHECKLIST.md` task T4.1.1 and verify `task lint`, `task check`, and `task test`.
