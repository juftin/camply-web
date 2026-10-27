# CONFIGURATION: Environment Variables & Settings

This document defines all environment variables used by the `camply` monorepo. Agents and contributors should use this as a reference when setting up local or production environments.

## ⚙️ Core Configuration

All backend environment variables are prefixed with `CAMPLY_` to avoid conflicts.
They are defined in `backend/packages/backend/backend/config.py` via `pydantic-settings`.

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

Database config uses `CAMPLY_DB_` prefix (defined in `backend/packages/db/db/config.py`):

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

Use Pages project root `frontend`, build command `pnpm run build`, and output directory `dist`. Pages discovers `frontend/functions/api/[[path]].ts` alongside the frontend sources; deploy through Pages Git integration or Wrangler so the Function is included. Uploading only `dist` as static files does not include the proxy. The build copies `public/_routes.json` to `dist` to invoke the Function only for `/api` paths. Locally, build assets with `task frontend:build:static`; the Vite development server continues using its own `/api` proxy.

Use Node 24, selected by `frontend/.node-version`, and set `PNPM_VERSION=10.34.6` in both production and preview build environments. If the Pages project already overrides `NODE_VERSION`, set it to `24`. An existing `npm run build` command remains compatible with pnpm-installed dependencies.

Set the Pages Functions compatibility date to `2024-11-11` or later (or enable `cache_option_enabled`) in the project's runtime settings. The proxy uses the standard Fetch `cache: "no-store"` option to bypass upstream caching; [older runtimes require that compatibility flag](https://developers.cloudflare.com/changelog/post/2024-11-11-cache-no-store/).

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

| Variable            | Description                   | Default  |
| ------------------- | ----------------------------- | -------- |
| `POSTGRES_USER`     | DB Username                   | `camply` |
| `POSTGRES_PASSWORD` | DB Password                   | `camply` |
| `POSTGRES_DB`       | DB Name                       | `camply` |
| `BACKEND_VERSION`   | Docker image tag for backend  | `local`  |
| `FRONTEND_VERSION`  | Docker image tag for frontend | `local`  |

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
