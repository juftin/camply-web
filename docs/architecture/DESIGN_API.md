# API Contract and Security

`camply.server.app:app` serves a FastAPI JSON API (`ORJSONResponse` + Pydantic v2 schemas) that drives OpenAPI TypeScript codegen for the React frontend (`task api:generate`).

## Authentication modes

`CAMPLY_AUTH_MODE` selects authentication independently of `CAMPLY_ENVIRONMENT`:

- **`none` (default):** Signs every request in as the shared admin account and hides login/logout UI.
- **`session`:** Authenticates via `POST /api/login` using signed HTTP-only JWT session cookies (`jti` backed by `user_sessions`) and `X-CSRF-Token` validation on mutations. Password changes or `DELETE /api/me/sessions/{id}` revoke sessions immediately.
- **`auth0`:** Validates RS256 bearer tokens against Auth0 JWKS (with bounded `/userinfo` fallback caching when email claims are absent). The React SDK keeps tokens strictly in memory (`cacheLocation="memory"`, refresh token rotation) to avoid `localStorage` XSS exposure; `Axios` retries at most one `401` on idempotent `GET`/`HEAD`/`OPTIONS` calls and never replays mutations.

camply never merges accounts by email automatically: verified email collisions across distinct identities return `409 Conflict` (`ERR_EMAIL_CONFLICT`), and missing verified emails return `403 Forbidden`.

## Invite-only access

When `CAMPLY_INVITE_ONLY=true`, `/api/scans` routes require `is_invited=true`. Uninvited users can submit `POST /api/request-access` (which alerts eligible admins via Pushover or ntfy) and admins approve or reject requests via `/api/admin/access-requests`.

## Core endpoint groups

| Prefix                                                                  | Audience                | Purpose                                                                                                      |
| ----------------------------------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| `/api/search*`, `/api/providers*`, `/api/campground*`, `/api/rec-area*` | Public                  | Explore search, bounded viewport map queries (`/api/search/map*`), and catalog metadata                      |
| `/api/me*`, `/api/login`, `/api/logout`, `/api/change-password`         | Authenticated           | Profile, Pushover/ntfy preferences, test alerts (`POST /api/me/notifications/test`), and session management  |
| `/api/scans*`                                                           | Authenticated + Invited | Campground and recreation-area scan CRUD, optimistic locking (`row_version`), and filtered live results      |
| `/api/admin/*`                                                          | Admin                   | User/scan management, access-request review, audit logs, Celery/standalone operations, and Prometheus trends |
| `/api/ping`, `/api/health`                                              | Public                  | Liveness (`/api/ping`) and DB + runtime readiness (`/api/health`, returns `503` when unhealthy)              |

## Standalone static serving

When `CAMPLY_RUNTIME_MODE=standalone`, FastAPI serves bundled frontend assets at `/` and static docs at `/docs/`. API misses under `/api/*` never fall back to SPA HTML, missing `/docs/*` paths return `404`, and `/metrics` is disabled.

See [Runtime & Packaging](../operations/RUNNING.md) for role commands and [Environment Variables](../operations/CONFIGURATION.md) for all auth and CORS settings.
