# CONFIGURATION: Environment Variables & Settings

This document defines all environment variables used by the `camply` monorepo. Agents and contributors should use this as a reference when setting up local or production environments.

## Python installation capabilities

Python >=3.11 is supported; development, primary CI, Docker, and release
runtimes default to 3.14. Base `camply` provides provider and SQLite APIs.
The `server`, `distributed`, `postgres`, and `sentry` extras independently add
HTTP, Celery/Redis, Psycopg, and Sentry dependencies. Selecting an extra does
not start or provision services. Configuration keys remain unchanged.

Use `camply[server]` for the API without broker integration and
`camply[server,distributed,postgres,sentry]` for the existing full stack.
API-only installs retain scan management, but scheduled checks need workers,
beat, and Valkey/Redis. Missing distributed support makes operations reads
unavailable and task detail/dispatch return authorized HTTP 503 responses.
A configured Sentry DSN needs the `sentry` extra; PostgreSQL engine creation
needs `postgres`. See [backend installation](../../README.md).

## ⚙️ Core Configuration

All backend environment variables are prefixed with `CAMPLY_` to avoid conflicts.
They are defined in `src/camply/server/config.py` via `pydantic-settings`.

| Variable                           | Description                                                   | Default                                                            |
| ---------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------ |
| `CAMPLY_ENVIRONMENT`               | Deployment stage (`local`, `development`, `production`)       | `local`                                                            |
| `CAMPLY_DEBUG`                     | Enable debug logs and FastAPI docs                            | `true`                                                             |
| `CAMPLY_SENTRY_DSN`                | Sentry DSN for error tracking                                 | `None` (disabled)                                                  |
| `CAMPLY_SENTRY_TRACES_SAMPLE_RATE` | Sentry traces sample rate                                     | `0.0`                                                              |
| `CAMPLY_AUTH_MODE`                 | Owner-selected authentication (`none`, `session`, or `auth0`) | `none`                                                             |
| `CAMPLY_INVITE_ONLY`               | Require invited status for scan operations                    | `false`                                                            |
| `CAMPLY_LOGIN_USERNAME`            | Shared username for in-app password login                     | `None`                                                             |
| `CAMPLY_LOGIN_PASSWORD`            | Shared password for in-app password login                     | `None`                                                             |
| `CAMPLY_SESSION_SECRET`            | Cookie signing secret (at least 32 characters)                | `None`                                                             |
| `CAMPLY_SESSION_MAX_AGE`           | Absolute session lifetime in seconds                          | `43200`                                                            |
| `CAMPLY_SESSION_COOKIE_SECURE`     | Require HTTPS for session cookies                             | `true`                                                             |
| `CAMPLY_CORS_ORIGINS`              | JSON list of trusted frontend origins for CORS and login      | localhost:5173 and camply.juftin.dev                               |
| `CAMPLY_CORS_ORIGIN_REGEX`         | Regex of additional trusted origins for CORS and login        | Local/Tailscale origins and HTTPS camply-81r.pages.dev deployments |
| `CAMPLY_ADMIN_EMAIL`               | Shared identity for automatic login and password sessions     | `admin@camply.local`                                               |
| `CAMPLY_AUTH0_DOMAIN`              | Auth0 tenant domain (e.g., `dev-xyz.us.auth0.com`)            | `None`                                                             |
| `CAMPLY_AUTH0_AUDIENCE`            | Auth0 API Audience/Identifier                                 | `None`                                                             |
| `CAMPLY_AUTH0_CLIENT_ID`           | Auth0 frontend Client ID                                      | `None`                                                             |

Database config uses `CAMPLY_DB_` prefix (defined in `src/camply/db/config.py`):

| Variable               | Description        | Default                           |
| ---------------------- | ------------------ | --------------------------------- |
| `CAMPLY_DB_DRIVERNAME` | Database driver    | `sqlite+aiosqlite`                |
| `CAMPLY_DB_USERNAME`   | Database username  | `camply`                          |
| `CAMPLY_DB_HOST`       | Database host/path | `~/.local/share/camply/camply.db` |
| `CAMPLY_DB_DATABASE`   | Database name      | `camply`                          |

Valkey/Celery & Operations config:

| Variable                    | Description                                                                                                             | Default                     |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `CAMPLY_VALKEY_URL`         | Valkey connection string for Celery                                                                                     | `redis://localhost:6379/0`  |
| `CAMPLY_HEARTBEAT_INTERVAL` | Heartbeat interval for periodic campsite availability discovery in seconds                                              | `300` (5 minutes)           |
| `CAMPLY_TARGET_COOLDOWN`    | Minimum seconds elapsed before an existing target is eligible for re-checking                                           | `55`                        |
| `CAMPLY_NOTIFICATION_MODE`  | `summary`: one alert per saved scan/check with new matching openings; `direct`: individual provider booking-link alerts | `summary`                   |
| `CAMPLY_APP_URL`            | Public frontend base URL, including an optional path prefix, used by summary alerts                                     | `https://camply.juftin.dev` |

Summary alerts link to `/dashboard/scans/{scan_id}#results` under `CAMPLY_APP_URL`. Set this on the **Celery worker** to the address recipients can open, for example `https://camply.example.com` or `https://example.com/camply/`. Use an absolute HTTP(S) base URL without credentials, a query, or a fragment. Login preserves the scan destination. Docker Compose defaults to `http://localhost:5173`; use a reachable hostname when opening notifications on another device.

For local deployments that prefer the previous individual alerts with booking-provider links, set `CAMPLY_NOTIFICATION_MODE=direct` on the worker. The default remains `summary` in every environment. Unchanged availability does not alert again; newly matching nights can alert, and openings that disappear and return can alert again. Different saved scans receive separate summaries. Direct mode can produce multiple alerts per check.

The campsite-details migration is required before starting the updated API/worker: run `task backend:migration-upgrade`. Existing snapshot attributes remain unknown until the next successful check; unknown types/electric hookups do not satisfy restrictive filters. Fresh snapshots replace them automatically. The results list, dashboard counts and alerts use the same saved filters and minimum consecutive stay.

---

## Runtime selection

| Variable              | Description                                                    | Default                                                                       |
| --------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `CAMPLY_RUNTIME_MODE` | `distributed` or `standalone`; independent of auth/environment | `distributed`                                                                 |
| `CAMPLY_FRONTEND_DIR` | Absolute directory containing a built UI; standalone only      | Installed `camply/server/static`; development task uses root `build/frontend` |

`camply serve` (or `task standalone:run` in a checkout) selects standalone, validates file-backed SQLite and assets, migrates, and binds to loopback; use `camply serve --host <address> --port <port>` to override the listener, or pass the flags after `--` to the Task wrapper. `CAMPLY_DB_HOST` is the SQLite file path; the default comes from `platformdirs.user_data_dir("camply")`, including on macOS. `:memory:` and PostgreSQL are rejected by the standalone launcher. `WEB_CONCURRENCY`, `GUNICORN_WORKERS`, and `UVICORN_WORKERS` must be unset or `1`, and `GUNICORN_RELOAD` must be disabled. Never run multiple standalone instances against the same file. The launcher defaults `CAMPLY_APP_URL` to its HTTP listener for summary links; set it explicitly to your public HTTPS URL or path prefix when using a reverse proxy.

Standalone uses the existing positive `CAMPLY_HEARTBEAT_INTERVAL` (300 seconds) and `CAMPLY_TARGET_COOLDOWN` (55 seconds). No broker or Prometheus URL is queried; distributed settings continue to apply in distributed mode. Local admin history retains up to 1,000 attempts for 24 hours and clears on restart. Pending delivery is stored separately in SQLite. Both runtimes honor `CAMPLY_NOTIFICATION_MODE` (`summary` by default, or `direct`); summaries are revalidated and recounted before standalone delivery. Set `PUSHOVER_APP_TOKEN` and the current user's Pushover key for delivery. Missing credentials skip alerts rather than reporting success. Runtime selection does not enable login or invitation checks; configure authentication explicitly as below.

## Nginx frontend proxy

`camply serve frontend` reads `CAMPLY_BACKEND_URL` at startup and renders it into the packaged Nginx `proxy_pass` directive. The default is `http://backend:8000` when the variable is unset or empty. Compose forwards this variable to the frontend container, and downstream deployments can pass it directly to the CLI or container environment.

```bash
CAMPLY_BACKEND_URL=http://api.internal:9000 camply serve frontend
```

Use an origin without a trailing slash to retain `/api/`: `/api/health` forwards to `http://api.internal:9000/api/health`. A URL with a URI path uses [Nginx's normal prefix replacement rules](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass). Restart the frontend after changing the variable. Browser requests continue to use the frontend's same-origin `/api/` endpoint.

HTTPS upstreams receive their configured hostname as TLS SNI, allowing connections to servers that require it. Run `task backend:nginx:test` to verify the packaged Nginx configuration against synthetic HTTP and SNI-required HTTPS upstreams. The test requires Docker and OpenSSL, uses `nginx:stable-alpine` by default, and accepts `CAMPLY_NGINX_SMOKE_IMAGE` to reuse another locally available Nginx image. CI runs it alongside the runtime health smoke.

## Distributed startup

`camply serve backend` finishes database migrations before launching the API. Compose workers
and beat depend on the backend's health check as well as healthy PostgreSQL and Valkey, so they
cannot process tasks against a schema still being migrated. Kubernetes deployments should make
worker/beat startup wait for the migrated API's health endpoint or an explicit migration Job;
a database TCP check alone does not establish schema readiness.

Compose runs `camply serve beat --sync-providers`. The opt-in flag enqueues
`camply.catalog.sync_all_providers` with a ten-minute expiry before replacing the CLI with Celery
beat. Dispatch uses the same Python environment as the CLI, and a nonzero dispatch exit stops
startup. Bare `camply serve beat` keeps its existing schedule without dispatching an initial sync.
The flag requests work asynchronously; it does not wait for provider ingestion to finish.
Workers and beat never apply database migrations, including when the sync flag is set.

## Service health checks

| Command                             | Default check                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| `camply serve healthcheck`          | Standalone `http://127.0.0.1:8000/api/health`                                   |
| `camply serve healthcheck backend`  | API `http://127.0.0.1:8000/api/health`                                          |
| `camply serve healthcheck frontend` | Nginx `http://127.0.0.1:8080/healthz`                                           |
| `camply serve healthcheck worker`   | Directed Celery ping to `celery@<local hostname>` through the configured broker |
| `camply serve healthcheck beat`     | Fresh heartbeat from a live local scheduler PID                                 |

Each probe prints `healthy` and exits 0 on success; an unhealthy service exits 1 with a short diagnostic on stderr. Invalid CLI usage exits 2. The probes do not migrate databases or dispatch application tasks. HTTP and beat checks work with the base package; the worker check requires `camply[distributed]`. Beat PID checks require Unix. Help never requires optional runtime dependencies. Run each local probe in the same container and environment as its serving role.

HTTP probes accept `--url` for a custom listener and `--timeout` for the network timeout (5 seconds by default). They require a 2xx status, reject redirects, and ignore environment HTTP proxies. For example, `camply serve healthcheck --url http://127.0.0.1:9000/api/health` matches standalone serving on port 9000. An init container can use `camply serve healthcheck backend --url http://backend:8000/api/health` to wait for the API. The distributed API endpoint reports HTTP liveness; it does not verify PostgreSQL or Valkey. Standalone additionally checks its SQLite connection and local runner. Frontend checks only Nginx, independently of its upstream. Keep separate infrastructure/readiness probes when database or broker availability matters.

The worker probe uses the current Python environment to run Celery inspection, requests a reply from exactly one named worker, and enforces a subprocess deadline with `--timeout` (5 seconds by default). Another healthy replica cannot satisfy the default local probe. If serving with a custom `--hostname`, pass its expanded node name via `camply serve healthcheck worker --destination custom@hostname`. Worker remote control must be enabled. A busy solo pool can delay control replies; size the timeout accordingly or use the default prefork pool. This checks worker control responsiveness and broker connectivity, rather than completion of an application task.

`camply serve beat` uses a persistent Celery scheduler that atomically writes its PID and timestamp after each completed scheduling tick. Its default maximum sleep is 30 seconds. The probe checks that PID and requires a timestamp no more than 60 seconds old. Set `CAMPLY_BEAT_HEALTH_FILE` on both serving and probing processes to override the default `camply-beat-health.json` under Python's temporary directory, or pass `--heartbeat-file` to the probe. The directory must be writable by beat; keep the marker local to one beat instance and its PID namespace. Startup clears old state and clean shutdown removes the marker. A forced kill leaves a marker that fails the PID check. Use `--max-age` to adjust the freshness window when forwarding a larger `--max-interval` to beat. Replacing beat's `--scheduler` disables this heartbeat unless the replacement implements the same contract. A fresh marker confirms scheduler-loop progress, not successful broker publication or worker task execution.

Compose configures these probes per role, with a 10-second outer timeout and startup grace periods. The shared image has no role-specific Dockerfile `HEALTHCHECK`; standalone or other downstream deployments should select the matching command. Kubernetes can use these commands as exec probes or retain the same HTTP endpoints as in [the downstream deployment example](https://github.com/juftin/home-ops/pull/257). Run `task backend:healthcheck:test` for real worker targeting, broker-loss detection, beat stall detection, and shutdown verification; CI runs the same smoke test.

## Process shutdown

Serving commands use process replacement (`exec`) to run in the foreground. Gunicorn, Celery worker/beat, and Nginx retain their native signal handling and child-process management. Bare `camply serve` runs Uvicorn in the main thread with one worker, so its normal shutdown invokes application lifespan cleanup: stop local scheduling, drain/cancel background work, and close database resources.

Compose sends `SIGTERM` to backend/worker/beat and `SIGQUIT` to frontend Nginx. Nginx treats `SIGTERM` as fast shutdown and `SIGQUIT` as graceful shutdown; changing the shared image's default stop signal would also affect Python roles. All application services have a one-minute `stop_grace_period`. For `docker run`, use `--stop-timeout 60`; add `--stop-signal SIGQUIT` for `camply serve frontend`. Extend the worker's Compose grace period when tasks need more than a minute to finish.

`SIGKILL` cannot be caught, forwarded, or used for cleanup. Docker forcibly kills a container after its grace period, and in-flight requests/tasks can be interrupted. Outside containers, use a service manager that owns all descendant processes (for example [systemd with `KillMode=mixed`](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html)): signal the master first for graceful shutdown, then kill the complete service if the grace period expires. Killing only a master PID does not generally guarantee all descendants stop. Process replacement avoids an extra launcher parent but does not change OS process-group semantics. These behaviors follow [Docker's stop policy](https://docs.docker.com/reference/cli/docker/container/stop/), [Nginx signal handling](https://nginx.org/en/docs/control.html), and [Celery shutdown semantics](https://docs.celeryq.dev/en/stable/userguide/workers.html#stopping-the-worker).

## 🔒 Authentication (Toggleable)

The instance owner chooses `CAMPLY_AUTH_MODE`. `CAMPLY_ENVIRONMENT` does not select or override authentication. HTTP Basic authentication is never used; `basic` and the old `local` auth mode are rejected.

### Automatic single-user login (`none`, default)

Every request automatically uses `CAMPLY_ADMIN_EMAIL`. There is no password or login screen; anyone who can reach the instance uses the shared admin account. The frontend hides sign-in, signup, and sign-out controls. This is also the default local development experience.

### In-app password login (`session`)

Set `CAMPLY_AUTH_MODE=session`, `CAMPLY_LOGIN_USERNAME`, `CAMPLY_LOGIN_PASSWORD`, and `CAMPLY_SESSION_SECRET` (at least 32 characters). The app shows a username/password form, posts JSON to `/api/login`, and remembers login through a signed, expiring HTTP-only cookie. No Basic header or browser password prompt is involved. Administrators can provision additional local accounts through User Management; public signup is unavailable.

The configured credentials bootstrap the `CAMPLY_ADMIN_EMAIL` account. After an administrator resets its password or the account changes its password, the stored password replaces `CAMPLY_LOGIN_PASSWORD` for authentication. The account can then sign in with its email or the configured username and its new password. In session mode, its administrator role comes from the database, so another administrator can demote it. Automatic login always grants the configured account administrator access. Password-change requirements apply only in session mode, including when switching authentication modes.

Create User and Reset Password dialogs offer **Generate Password** and **Copy** actions. Generated passwords use browser cryptographic randomness and are visible only in the open dialog; copy them before saving or closing. Closing the dialog or successfully saving clears the generated value. Manually entered passwords remain masked. Generated passwords are not stored in browser storage or returned by the API after saving.

The local Docker Compose stack supplies `admin` / `camply` and a development signing secret when these variables are unset. It also sets `CAMPLY_SESSION_COOKIE_SECURE=false` for its HTTP frontend. These known values are only for local development. Override the username, password, and signing secret before exposing the stack to other users, and set `CAMPLY_SESSION_COOKIE_SECURE=true` when serving it over HTTPS.

Cookies default to `Secure` and `SameSite=Strict`. For an HTTP-only local setup, explicitly set `CAMPLY_SESSION_COOKIE_SECURE=false`. Serve the frontend and API on the same site (the Vite `/api` proxy supports local development); configure `CAMPLY_CORS_ORIGINS` for your frontend origin. `CAMPLY_CORS_ORIGIN_REGEX` also permits local development and Tailscale origins by default; both CORS and password login use this policy. A separate CSRF cookie supplies the request header required for authenticated mutations. Passwords are not retained by the frontend.

The frontend verifies the session through `/api/me` after login before opening the dashboard. A successful `/api/login` response alone does not prove the browser accepted the cookies. If verification fails or scan requests return 401 immediately after login, check HTTPS versus `CAMPLY_SESSION_COOKIE_SECURE`, browser cookie settings, and whether the frontend and API share the same site. For local development, use the `/api` proxy rather than a separate API hostname. Scan queries do not automatically retry 401/403 responses.

Sessions expire after `CAMPLY_SESSION_MAX_AGE` seconds. A scan query returning 401 clears the cached profile and scan data and returns the user to sign-in; a new login fetches scans again. Logout removes both session and CSRF cookies. Changing the configured username, password, or signing secret invalidates existing sessions. Resetting or changing a stored password invalidates every earlier cookie for that account, even when the same password is assigned again. A successful password change issues fresh cookies to the current browser while preserving its CSRF token. Cookies from before credential versioning was introduced require a new login. Clearing a browser session does not individually revoke a copied cookie before expiry; individual session revocation remains a follow-up.

### Auth0 (`auth0`)

Set `CAMPLY_AUTH_MODE=auth0`. All three of `CAMPLY_AUTH0_DOMAIN`, `CAMPLY_AUTH0_AUDIENCE`, and `CAMPLY_AUTH0_CLIENT_ID` are required, including when the environment is local. The frontend obtains these public settings from `/api/auth-config` and requests access tokens for the configured API audience. Configure Auth0 callback/logout URLs for the frontend origin and base path. Signup is available only in Auth0 mode.

### Cloudflare Pages frontend

`src/frontend/wrangler.jsonc` defines Pages project `camply-81r`, compatibility date `2024-11-11`, and output `dist` relative to that configuration. Functions remain at `src/frontend/functions/api/[[path]].ts`. Root `task frontend:pages:check` validates an isolated local build/Function without credentials, and `task frontend:pages:dev` serves the built UI through Wrangler with `--cwd src/frontend`. The Vite development server retains its own `/api` proxy.

When migrating Git-integrated Pages, change the hosted project root to `src/frontend`, set its build command to `cd ../.. && pnpm install --frozen-lockfile && CAMPLY_STANDALONE_BUILD=1 VITE_API_URL=/api pnpm run build`, and use output `dist`. Root `package.json` pins Node 24 and pnpm 12.15.0; explicitly set `NODE_VERSION=24` and matching `PNPM_VERSION=12.15.0` in both production and preview build environments because those files are above the Pages project root. Preserve existing production/preview `CAMPLY_API_ORIGIN` and protected bindings when adopting file-based configuration. The Wrangler file does not update dashboard build-root settings or deploy automatically.

Deploy through Pages Git integration or Wrangler so the Function is included; uploading only `build/frontend` through a static-files mechanism omits it. The build copies `src/frontend/public/_routes.json` into output to invoke the Function only for `/api` and `/api/*`. The checked-in compatibility date supports standard Fetch `cache: "no-store"`; [older runtimes require the corresponding flag](https://developers.cloudflare.com/changelog/post/2024-11-11-cache-no-store/).

| Variable            | Where to set it                                                                        | Value                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `CAMPLY_API_ORIGIN` | Pages Settings → Variables and Secrets, for each Production/Preview environment in use | HTTPS backend origin, e.g. `https://api.example.com`, without `/api`, credentials, or query strings |
| `VITE_API_URL`      | Pages build environment                                                                | Unset (defaults to `/api`) or `/api`; an absolute backend URL bypasses the proxy                    |

Redeploy after changing these settings. The browser sends all API traffic to the Pages frontend host; the Function forwards it to the backend and relays both session cookies unchanged. The session cookie remains `HttpOnly`, `Secure`, and `SameSite=Strict`, and the readable CSRF cookie belongs to the frontend host. The backend must still trust the frontend origin through `CAMPLY_CORS_ORIGINS` or `CAMPLY_CORS_ORIGIN_REGEX`, since the proxy preserves `Origin` for password-login validation. API responses are not cached; missing/invalid proxy configuration returns 503, and an unreachable backend returns 502.

The default backend regex trusts `https://camply-81r.pages.dev` and its HTTPS deployment-hash and branch-alias origins, such as `https://da37cb45.camply-81r.pages.dev`. It does not trust other Pages projects, HTTP Pages origins, or nested subdomains. If the backend overrides `CAMPLY_CORS_ORIGIN_REGEX`, include the project-scoped pattern `https://(?:[a-z0-9-]+\.)?camply-81r\.pages\.dev` in the override or remove the override to use the default. Self-hosted deployments using another Pages project must explicitly configure their own trusted origins. Restart/redeploy the backend after changing this policy; a login response of `403 Untrusted login origin` indicates the frontend origin is not trusted.

See the [Pages Functions setup](https://developers.cloudflare.com/pages/functions/get-started/) and [environment variable documentation](https://developers.cloudflare.com/pages/functions/bindings/#environment-variables).

### Optional invite-only access

Set `CAMPLY_INVITE_ONLY=true` to require `is_invited=true` for all scan operations. It defaults to `false`: authenticated users may manage their scans without invitations. Public browsing and authenticated profile access remain available in either case. The shared admin for `none` and `session` is invited when created.

The Python model and API use `is_invited`; its existing database column remains `is_early_access_user` to preserve stored grants without a migration. Invitation requests are collected through `/api/request-access`.

**TODO:** Implement approval/revocation, safe matching of requests to verified user identities, and invitation notifications. Requests currently remain pending; they do not grant access or send email.

---

## 🔔 Notifications

### Pushover (MVP)

| Variable             | Description                                    |
| -------------------- | ---------------------------------------------- |
| `PUSHOVER_APP_TOKEN` | The API Token for your Pushover "Application". |

### Apprise (Legacy/Future)

| Variable       | Description                                      |
| -------------- | ------------------------------------------------ |
| `APPRISE_URLS` | Comma-separated list of Apprise-compatible URLs. |

---

## 📈 Monitoring & Observability

### Native Admin UI Monitoring (Prometheus-backed)

The Admin UI provides native monitoring dashboards for usage trends, API latency/errors, worker throughput/outcomes, and provider performance, querying an internal Prometheus instance via FastAPI proxy (`GET /api/admin/trends`). Grafana is decommissioned and no longer deployed.

| Variable                | Description                | Default                 |
| ----------------------- | -------------------------- | ----------------------- |
| `CAMPLY_PROMETHEUS_URL` | Prometheus server base URL | `http://localhost:9090` |

### Sentry

| Variable                    | Description                                   |
| --------------------------- | --------------------------------------------- |
| `SENTRY_DSN`                | The DSN for error tracking (Optional).        |
| `SENTRY_TRACES_SAMPLE_RATE` | Percentage of traces to capture (0.0 to 1.0). |

---

## 🏗️ Docker & Infrastructure

These variables are primarily used in `docker-compose.yaml`.

| Variable            | Description                    | Default  |
| ------------------- | ------------------------------ | -------- |
| `POSTGRES_USER`     | DB Username                    | `camply` |
| `POSTGRES_PASSWORD` | DB Password                    | `camply` |
| `POSTGRES_DB`       | DB Name                        | `camply` |
| `CAMPLY_VERSION`    | Shared camply Docker image tag | `local`  |

## Optional Community Pages (Public Frontend Build Setting)

Ethos (`/ethos`) and Contribute (`/contribute`) are disabled by default. Set `VITE_ENABLE_COMMUNITY_PAGES=true` in the frontend build environment to enable both pages and their desktop/mobile navigation, Contact card, and FAQ link. Only the exact value `true` enables them; unset, `false`, and other values keep them disabled. Direct visits to disabled pages redirect to the home page.

For local development, run `VITE_ENABLE_COMMUNITY_PAGES=true task frontend:dev`. For static hosting (including Cloudflare Pages), set the variable in the build environment and rebuild. Docker accepts the same build argument, and Compose forwards it with a default of `false`. A root backend `.env` is not automatically a Vite environment file. The visual snapshot runner enables the pages to retain their visual coverage; application tests cover both settings.

## Maps (Public Frontend Build Settings)

All maps use MapLibre GL JS and default to keyless OpenStreetMap raster tiles. No Google Maps account or key is needed. These public Vite values are embedded in the frontend bundle; never put secrets in them. Set them in the frontend build environment (or Compose build arguments) and rebuild after a change. A root backend `.env` is not automatically a Vite environment file.

| Variable                    | Default                                          | Meaning                                                                                 |
| --------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `VITE_MAP_TILE_URL`         | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Compatible 256px raster XYZ tiles in EPSG:3857; HTTPS or same-origin root-relative path |
| `VITE_MAP_ATTRIBUTION_TEXT` | © OpenStreetMap contributors                     | Plain-text source credit                                                                |
| `VITE_MAP_ATTRIBUTION_URL`  | `https://www.openstreetmap.org/copyright`        | HTTPS source attribution/license page                                                   |
| `VITE_MAP_MAX_NATIVE_ZOOM`  | `19`                                             | Integer 0–19; tiles may be overzoomed up to map zoom 19                                 |

A custom tile URL requires its own attribution text and link. For a self-hosted source, use its XYZ endpoint and applicable contributor credit; for example `/tiles/{z}/{x}/{y}.png` with a source-specific HTTPS license page. Invalid settings produce a recoverable map error while list search stays available. Docker builds accept the same four argument names; Compose forwards their process/environment settings.

Open-source map software and openly licensed map data are separate from tile hosting costs and capacity. The default public service has no SLA; follow [OpenStreetMap's tile usage policy](https://operations.osmfoundation.org/policies/tiles/) for linked attribution, browser caching, origin referrers, and no bulk/offline downloading. Choose a compatible hosted or self-hosted service for production capacity beyond those terms. Map requests do not use the authenticated API client, attach authorization/CSRF headers, or submit scan settings. External tile hosts still see client IP addresses and requested tile coordinates; self-hosting avoids that external dependency. Device location is not requested.

MapLibre GL JS requires WebGL 2. If the browser cannot create a graphics context, the map shows a local error with retry and the list remains usable. The renderer worker is bundled as a same-origin Vite asset, including under a repository subpath. Cross-origin raster sources must permit CORS for the frontend origin (the default OSM source does); self-hosted sources on the same origin need no CORS configuration. If you enforce a Content Security Policy, permit the bundled same-origin worker and the configured tile origin.
