# Worker VPN and proxy rotation for provider requests

## User stories

- Operators run high-frequency availability scans across dozens of parks without risking IP bans or WAF rate-limiting from upstream reservation providers (Recreation.gov, ReserveCalifornia, UseDirect).
- Operators keep the default application footprint lightweight and zero-overhead: standard local development and single-user instances run without VPN sidecars or extra dependencies by default.
- Operators securely configure commercial VPN credentials (NordVPN or any standard OpenVPN provider) via Docker Compose profiles and environment variables without committing secrets.
- Operators observe the active egress IP, VPN connection health, and rotation history in the Admin UI, with the ability to trigger on-demand IP rotation if a provider degrades.

## Requirements

### Default-off execution & Compose isolation
- Provider requests MUST connect directly to upstream reservation APIs by default (`CAMPLY_PROXY_ENABLED=false`). When disabled, no proxy sidecars, network queries, or Valkey proxy keys are used.
- VPN proxy sidecars MUST be isolated under Docker Compose `profiles: ["vpn"]`. Standard development (`task dev`, `docker compose up`) MUST NOT start VPN containers unless explicitly commanded via `--profile vpn`.

### Dual-proxy zero-downtime rotation
- When enabled (`CAMPLY_PROXY_ENABLED=true`), two Gluetun proxy sidecars (`vpn-proxy-alpha` and `vpn-proxy-beta`) MUST run in parallel, exposing local HTTP proxies on port 8888 and control APIs on port 8000.
- Rotation MUST occur in the background on the standby proxy before switching active traffic: the standby container reconnects via OpenVPN, validates its new public IP and country, and then updates the active proxy pointer in Valkey. In-flight requests on the active proxy drain without connection resets.
- OpenVPN service credentials (`OPENVPN_USER` / `OPENVPN_PASSWORD`) MUST authenticate the VPN tunnels, with exit nodes restricted to the United States (`SERVER_COUNTRIES=United States`) to avoid provider geo-blocking.

### Rotation triggers
- **Periodic**: Celery Beat schedules background pool rotation every `CAMPLY_VPN_ROTATION_INTERVAL_MINUTES` (default 30).
- **Volume**: The proxy manager rotates after serving `CAMPLY_VPN_MAX_REQUESTS_PER_IP` (default 1000) requests to prevent statistical bot fingerprinting.
- **Reactive**: When an upstream provider returns HTTP 429 (Too Many Requests) or HTTP 403 (Forbidden/WAF Block), the worker immediately flags the current proxy IP as tainted, rotates to the standby proxy, and retries the request.

### Strict kill-switch enforcement
- `CAMPLY_VPN_STRICT` MUST default to `true` when proxy routing is enabled. If all configured VPN proxies are unreachable, provider tasks MUST raise a retryable `ProxyUnavailableError` rather than leaking the host server's cleartext IP address.

### Observability & Admin UI
- Expose `GET /api/admin/operations/vpn/status` returning active proxy name, egress IP, ISP, geolocation, and request count, and `POST /api/admin/operations/vpn/rotate` for manual rotation.
- Record Prometheus metrics for proxied requests, rotation counts, and egress IP changes.
- In the Admin Operations UI, display a status card showing egress IP details and a "Rotate IP Now" action when proxy routing is enabled, or a "Direct (No VPN)" badge when disabled.

## Scope limits

- Browser/user traffic to the FastAPI backend and frontend Vite app remains direct and unproxied.
- Internal microservice communication (PostgreSQL, Valkey, Celery broker, Prometheus) MUST remain on the Docker bridge network and never touch the VPN or proxy.
- Synthetic and unit tests MUST mock HTTP proxy transports; no live OpenVPN credentials or active VPN connections are required to run `task test`.
