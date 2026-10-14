# Tasks: Worker VPN and proxy rotation for provider requests

## Phase 1: Infrastructure & Environment Configuration
- [ ] T1.1 Add Gluetun dual-proxy services (`vpn-proxy-alpha`, `vpn-proxy-beta`) to `backend/docker-compose.yaml` under `profiles: ["vpn"]` using OpenVPN service credentials and US server filters.
- [ ] T1.2 Add proxy configuration fields to `backend/packages/worker/worker/config.py` and `backend/packages/backend/backend/config.py` (`CAMPLY_PROXY_ENABLED` default `false`, `CAMPLY_VPN_STRICT` default `true`).
- [ ] T1.3 Document OpenVPN credentials and proxy environment variables in `docs/agents/CONFIGURATION.md`.

## Phase 2: Transport & Proxy Manager
- [ ] T2.1 Implement `ProxyManager` in `backend/packages/providers/providers/proxy.py` with Valkey-backed state and Gluetun REST control client (`:8000`).
- [ ] T2.2 Refactor `RetryTransport` and `BaseProvider` in `backend/packages/providers/providers/base.py` to route through active proxy when enabled, and enforce strict kill-switch behavior (`ProxyUnavailableError`).
- [ ] T2.3 Add unit tests in `backend/packages/providers/tests/test_proxy.py` for direct connection defaults, proxy routing, and strict kill-switch error handling.

## Phase 3: Zero-Downtime Celery Rotation
- [ ] T3.1 Implement `camply.vpn.rotate_pool` Celery task in `backend/packages/worker/worker/tasks/` for background standby rotation and atomic Valkey pointer swap.
- [ ] T3.2 Schedule `camply.vpn.rotate_pool` in Celery Beat with configurable interval and volume thresholds.
- [ ] T3.3 Implement reactive failover in `RetryTransport` upon receiving HTTP 429 or HTTP 403 responses.
- [ ] T3.4 Add unit tests for Celery rotation task execution, lock contention, and standby IP verification.

## Phase 4: Observability & Admin Operations UI
- [ ] T4.1 Register Prometheus metrics for VPN proxy requests, rotations, and egress IP details.
- [ ] T4.2 Add FastAPI endpoints `GET /api/admin/operations/vpn/status` and `POST /api/admin/operations/vpn/rotate` in `backend/packages/backend/backend/routers/admin.py`.
- [ ] T4.3 Add VPN Status card and manual "Rotate IP Now" action to frontend Admin Operations page (`AdminOperations.tsx`).
- [ ] T4.4 Add frontend component and API integration tests for VPN admin controls.

## Phase 5: Verification & Quality Gates
- [ ] T5.1 Verify complete test suite passes without VPN containers running (`CAMPLY_PROXY_ENABLED=false`).
- [ ] T5.2 Verify synthetic proxy routing and kill-switch enforcement when `CAMPLY_PROXY_ENABLED=true`.
- [ ] T5.3 Update `docs/agents/CHECKLIST.md` task T4.1.1 and verify `task lint`, `task check`, and `task test`.
