# CONFIGURATION: Environment Variables & Settings

This document defines all environment variables used by the `camply` monorepo. Agents and contributors should use this as a reference when setting up local or production environments.

## ⚙️ Core Configuration

All backend environment variables are prefixed with `CAMPLY_` to avoid conflicts.
They are defined in `backend/packages/backend/backend/config.py` via `pydantic-settings`.

| Variable                           | Description                                                   | Default                              |
| ---------------------------------- | ------------------------------------------------------------- | ------------------------------------ |
| `CAMPLY_ENVIRONMENT`               | Deployment stage (`local`, `development`, `production`)       | `local`                              |
| `CAMPLY_DEBUG`                     | Enable debug logs and FastAPI docs                            | `true`                               |
| `CAMPLY_SENTRY_DSN`                | Sentry DSN for error tracking                                 | `None` (disabled)                    |
| `CAMPLY_SENTRY_TRACES_SAMPLE_RATE` | Sentry traces sample rate                                     | `0.0`                                |
| `CAMPLY_AUTH_MODE`                 | Owner-selected authentication (`none`, `session`, or `auth0`) | `none`                               |
| `CAMPLY_INVITE_ONLY`               | Require invited status for scan operations                    | `false`                              |
| `CAMPLY_LOGIN_USERNAME`            | Shared username for in-app password login                     | `None`                               |
| `CAMPLY_LOGIN_PASSWORD`            | Shared password for in-app password login                     | `None`                               |
| `CAMPLY_SESSION_SECRET`            | Cookie signing secret (at least 32 characters)                | `None`                               |
| `CAMPLY_SESSION_MAX_AGE`           | Absolute session lifetime in seconds                          | `43200`                              |
| `CAMPLY_SESSION_COOKIE_SECURE`     | Require HTTPS for session cookies                             | `true`                               |
| `CAMPLY_CORS_ORIGINS`              | JSON list of trusted frontend origins for CORS and login      | localhost:5173 and camply.juftin.dev |
| `CAMPLY_ADMIN_EMAIL`               | Shared identity for automatic login and password sessions     | `admin@camply.local`                 |
| `CAMPLY_AUTH0_DOMAIN`              | Auth0 tenant domain (e.g., `dev-xyz.us.auth0.com`)            | `None`                               |
| `CAMPLY_AUTH0_AUDIENCE`            | Auth0 API Audience/Identifier                                 | `None`                               |
| `CAMPLY_AUTH0_CLIENT_ID`           | Auth0 frontend Client ID                                      | `None`                               |

Database config uses `CAMPLY_DB_` prefix (defined in `backend/packages/db/db/config.py`):

| Variable               | Description        | Default                           |
| ---------------------- | ------------------ | --------------------------------- |
| `CAMPLY_DB_DRIVERNAME` | Database driver    | `sqlite+aiosqlite`                |
| `CAMPLY_DB_USERNAME`   | Database username  | `camply`                          |
| `CAMPLY_DB_HOST`       | Database host/path | `~/.local/share/camply/camply.db` |
| `CAMPLY_DB_DATABASE`   | Database name      | `camply`                          |

Valkey/Celery config:

| Variable     | Description                         | Default                    |
| ------------ | ----------------------------------- | -------------------------- |
| `VALKEY_URL` | Valkey connection string for Celery | `redis://localhost:6379/0` |

---

## 🔒 Authentication (Toggleable)

The instance owner chooses `CAMPLY_AUTH_MODE`. `CAMPLY_ENVIRONMENT` does not select or override authentication. HTTP Basic authentication is never used; `basic` and the old `local` auth mode are rejected.

### Automatic single-user login (`none`, default)

Every request automatically uses `CAMPLY_ADMIN_EMAIL`. There is no password or login screen; anyone who can reach the instance uses the shared admin account. The frontend hides sign-in, signup, and sign-out controls. This is also the default local development experience.

### In-app password login (`session`)

Set `CAMPLY_AUTH_MODE=session`, `CAMPLY_LOGIN_USERNAME`, `CAMPLY_LOGIN_PASSWORD`, and `CAMPLY_SESSION_SECRET` (at least 32 characters). The app shows a username/password form, posts JSON to `/api/login`, and remembers login through a signed, expiring HTTP-only cookie. No Basic header or browser password prompt is involved. This mode uses the shared admin account and has no signup.

Cookies default to `Secure` and `SameSite=Strict`. For an HTTP-only local setup, explicitly set `CAMPLY_SESSION_COOKIE_SECURE=false`. Serve the frontend and API on the same site (the Vite `/api` proxy supports local development); configure `CAMPLY_CORS_ORIGINS` for your frontend origin. `CAMPLY_CORS_ORIGIN_REGEX` also permits local development and Tailscale origins by default; both CORS and password login use this policy. A separate CSRF cookie supplies the request header required for authenticated mutations. Passwords are not retained by the frontend.

The frontend verifies the session through `/api/me` after login before opening the dashboard. A successful `/api/login` response alone does not prove the browser accepted the cookies. If verification fails or scan requests return 401 immediately after login, check HTTPS versus `CAMPLY_SESSION_COOKIE_SECURE`, browser cookie settings, and whether the frontend and API share the same site. For local development, use the `/api` proxy rather than a separate API hostname. Scan queries do not automatically retry 401/403 responses.

Sessions expire after `CAMPLY_SESSION_MAX_AGE` seconds. A scan query returning 401 clears the cached profile and scan data and returns the user to sign-in; a new login fetches scans again. Logout removes both session and CSRF cookies. Changing the configured username, password, or signing secret invalidates existing sessions. Cookies are stateless: clearing a browser session does not individually revoke a copied cookie before expiry; individual server-side revocation remains a follow-up.

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

Redeploy after changing these settings. The browser sends all API traffic to the Pages frontend host; the Function forwards it to the backend and relays both session cookies unchanged. The session cookie remains `HttpOnly`, `Secure`, and `SameSite=Strict`, and the readable CSRF cookie belongs to the frontend host. The backend must still trust the frontend origin through `CAMPLY_CORS_ORIGINS`, since the proxy preserves `Origin` for password-login validation. Set trusted preview origins explicitly if testing password login in Pages previews. API responses are not cached; missing/invalid proxy configuration returns 503, and an unreachable backend returns 502.

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
