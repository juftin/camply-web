# DESIGN_API: API Contract & Security

This document defines the interface between the `camply-backend` (FastAPI) and `camply-frontend` (React). It also outlines the security flow for Auth0 and optional invite-only access.

## Python package boundaries

The existing ASGI application is `camply.server.app:app`, enabled by the
`server` extra. This installation supports API browsing and scan management
with SQLite. Operations overview/task-list responses use
existing unavailable/error fields when `distributed` is absent unless `CAMPLY_RUNTIME_MODE=standalone` is active.

## Runtime and hosting contract

`CAMPLY_RUNTIME_MODE=standalone` serves built root-based frontend assets and the API from Python. Known API routes keep their normal errors, `/api/*` misses never become HTML, and `/metrics` is unavailable. HTML navigation falls back to the entry page for root/deep links; missing asset paths return 404. GET/HEAD are supported, other static methods return 405, hashed `/assets/` files are immutable, and entry HTML is not cached. Auth mode, CSRF, invitation checks, and administrator authorization remain independent of runtime.

`GET /api/health` checks database readiness in both runtimes with a two-second query budget, additionally checks supervised local loops in standalone, and returns HTTP 503 when unhealthy. Its existing response shape is unchanged. `/api/ping` remains dependency-independent liveness. Admin operations adds `runtime_mode`, `capabilities`, and local `scheduler_status`. Standalone returns `broker_connected: null`, unsupported reserved/scheduled counts as null, measured queue/running counts, and bounded local attempt history (1,000 entries/24 hours, cleared on restart). Historical trends use the existing unavailable response shape and are intentionally hidden by capability in the frontend. Failed loops display a real unhealthy state rather than a broker outage.

Administrator provider sync dispatches to the selected runtime. Repeated local sync requests share the active job identity and return promptly. Existing distributed broker/inspection/Prometheus behavior remains the default. See [admin response details](../specs/011-standalone-runtime/contracts/admin-api.md).

## 🎯 API Philosophy

1. **OpenAPI-First**: Every endpoint must be documented so that the frontend TypeScript client can be automatically generated.
2. **Standardized Responses**: All successful responses use `ORJSONResponse` for performance.
3. **Strict Validation**: Every request payload must be a Pydantic v2 model.
4. **Auth-Gated**: All user-specific endpoints are gated by the `CurrentUserDep` dependency.

---

## 🔒 Security & Middleware

### 1. Authentication and local development

The owner selects `none`, `session`, or `auth0` with `CAMPLY_AUTH_MODE`, independently of the environment. HTTP Basic authentication is unsupported.

- **Automatic login (`none`, default)**: every request uses the shared admin identity; no login/signup/logout UI.
- **Password sessions (`session`)**: the app posts username/password JSON to `POST /api/login`. The response contains the profile and sets a signed HTTP-only session cookie plus a CSRF cookie. The frontend confirms the cookie with `GET /api/me` before opening the dashboard; rejected cookies keep the user on the login form with setup guidance. Scan queries do not automatically retry 401/403 responses. A scan query's 401 clears the cached profile and scans, cancels any profile refresh, and returns the user to sign-in. Mutations require `X-CSRF-Token` matching the signed session. `POST /api/logout` clears the cookies. The shared account has no signup. Cookies have an absolute lifetime, and credential/secret changes invalidate them.
- **Auth0 (`auth0`)**: requests require an RS256 bearer token validated against issuer and API audience, and must carry `exp` and a nonempty `sub`. Invalid or expired credentials return 401; an unreachable or unusable JWKS endpoint returns 503 so clients can retry. Key sets are cached without caching keys indefinitely, ensuring dropped keys stop verifying once cache refreshes, and JWKS retrieval runs off the asyncio loop. Users are provisioned by verified email and subject on first access. The application starts sign-in on `/auth` and uses the Auth0 SDK.
- **Browser token storage & tradeoffs (`auth0`)**: `Auth0Provider` configures `cacheLocation="memory"`, `useRefreshTokens={true}`, and `useRefreshTokensFallback={true}` instead of `localStorage` or server-managed Auth0 BFF sessions. Keeping tokens strictly in memory prevents persistent token theft via XSS (`localStorage` / `sessionStorage`) and avoids adding stateful OAuth BFF token storage on the Python API. Tradeoff: in-memory tokens do not survive full page reloads or new tabs directly; silent session recovery across reloads relies on Auth0 Refresh Token Rotation (`useRefreshTokens`) backed by a silent Auth0 session iframe (`useRefreshTokensFallback`). When third-party cookies or storage partitioning (e.g., Safari ITP or strict browser privacy settings without an Auth0 Custom Domain) block the silent iframe, renewal returns `login_required` and prompts the user to sign in again rather than failing silently. Tokens and credentials are never persisted to `localStorage`/`sessionStorage` or logged to `console.*`.
- **Token acquisition classification & bounded session recovery (`auth0`)**:
  - Client-side `getAccessTokenSilently` errors are classified into `expired` (`login_required`, `consent_required`, `interaction_required`, `missing_refresh_token`, `invalid_grant`), `outage` (network errors, timeouts, IdP `5xx`), or `auth_failure` (`access_denied`, `invalid_scope`, and other OAuth errors).
  - On backend `401` responses in `auth0` mode, the Axios response interceptor allows at most **one** deduplicated token renewal (`getAccessTokenSilently({ cacheMode: "off" })`) only for safe idempotent requests (`GET`, `HEAD`, `OPTIONS`) that have not already retried (`!_retried`). Unsafe mutations (`POST`, `PUT`, `PATCH`, `DELETE`) are **never** automatically replayed on `401`; they fail immediately with a session-expired prompt and clear auth state.
  - When renewal fails with `expired`/`auth_failure` or a retried request still returns `401`, protected React Query caches (`["me"]`, `["scans"]`, `["admin"]`) are cleared and a clear sign-in error is surfaced without redirect or retry loops.
  - `503` verification-service responses (JWKS or `/userinfo` outages) and `outage` token errors keep the current user session intact and surface a temporary outage error (allowing at most one query retry). `403` (`ERR_VERIFIED_EMAIL_REQUIRED`, `ERR_INVITE_REQUIRED`, `ERR_PASSWORD_CHANGE_REQUIRED`) and `409` (`ERR_EMAIL_CONFLICT`) surface clear messages without query retries.
  - Protected queries (`useScans`, `useAdmin*`) wait until `isReady && Boolean(user)`, and switching Auth0 subjects (`auth0User.sub`) or signing out clears user/scan/admin caches so prior-account data cannot leak across sessions.
- **Trusted email provisioning & userinfo fallback**: Auth0 identity subjects (`sub`) are kept strictly separate from email addresses; `sub` is never used as an email placeholder. The backend only trusts verified emails. Email verification status is resolved by inspecting token claims (`email` and `email_verified`, including namespaced `https://camply/email` and `https://camply/email_verified`). When absent or unverified in claims, the backend falls back to `GET https://{auth0_domain}/userinfo` using the bearer token. Userinfo profiles are cached in memory (bounded to 1,000 entries, 10-minute TTL, keyed by the SHA-256 digest of the token; raw tokens are never logged). Upstream userinfo network or service failures return 503 so clients can retry. New users without a verified email receive `403 Forbidden` (`ERR_VERIFIED_EMAIL_REQUIRED`).
- **Duplicate emails & account-linking rules**: camply never automatically merges or links user identities solely because their email addresses match. Explicit proof-of-ownership account linking is out of scope. If an incoming identity presents a verified email already belonging to another account (such as an in-app password session user or a different Auth0 subject), the backend rejects the request with `409 Conflict` (`ERR_EMAIL_CONFLICT`) without modifying either user. Concurrent first-login races on the same `auth0_id` safely resolve to the winning record without 500 errors.
- **Email change synchronization**: For existing users matched by `auth0_id`, presenting a verified token with a new email address updates `User.email` (case-normalized) if unclaimed by another account. If the new email is already claimed, the request returns 409 `ERR_EMAIL_CONFLICT` without modifying the user. Unverified email changes are ignored and do not sync. Because subscriptions and preferences key on `User.id`, scans, notification settings, and invitation eligibility (`is_invited`) are fully preserved across email changes.
- **`GET /api/auth-config`**: public configuration returns `auth_mode`, `auth0_domain`, `auth0_client_id`, `auth0_audience`, `auto_login`, `signup_enabled`, and `invite_only`. The React SDK requests the returned audience. Auth0 mode must supply domain, audience, and client ID.
- **`GET /api/me`**: the profile exposes `is_invited`, `invitation_status` (`pending`, `approved`, `rejected`, or `null`), `is_admin`, and `scanning_enabled`. The existing database column remains `is_early_access_user` for compatibility with stored data.

Session cookies include a credential version derived by HMAC from the current salted password hash. Every authenticated session request checks this version against the database, so a password reset or change invalidates earlier cookies without adding a database column or exposing the hash. `POST /api/change-password` refreshes the current browser's cookies and preserves its CSRF token. Legacy cookies without a credential version require sign-in again. Stored bootstrap passwords replace the configured password for authentication; the configured username remains an alias. Session mode honors the stored administrator role, including bootstrap account demotions. Automatic login restores administrator access and ignores password-change flags; Auth0 also ignores these session-only flags.

### 2. Optional invite-only guard

`CAMPLY_INVITE_ONLY` defaults to `false`. When enabled, every `/api/scans` operation requires the user's `is_invited` flag. Uninvited authenticated callers receive `403` with `ERR_INVITE_REQUIRED`. The frontend gates dashboard and scan detail routes with the invitation request screen. Profiles and public metadata remain accessible. Existing scan ownership checks apply in both configurations.

### 3. Invitation requests and admin review

`POST /api/request-access` stores a pending request with a normalized lowercase email and optional `name`, accepting duplicate emails idempotently. When a new request is persisted (not on duplicate submissions), best-effort background notifications are sent via `ntfy` or `Pushover` to configured administrators (`is_admin=True`, `scanning_enabled=True`, and valid channel credentials). It does not grant access or send email.

On first-time Auth0 provisioning with a verified email, matching `AccessRequest` rows are linked via `user_id`; an `approved` request grants `is_invited=True`, while `pending` or `rejected` requests link `user_id` with `is_invited=False`. Existing uninvited Auth0 users who change to an unclaimed `approved` verified email also receive `is_invited=True`, unless they already have a `rejected` request. Unverified emails are rejected (`403 ERR_VERIFIED_EMAIL_REQUIRED`) and never claim approved requests. `GET /api/me` and `PATCH /api/me` expose `invitation_status` (`pending`, `approved`, `rejected`, or `null`) from the most recently updated matching request.

Administrators review requests via `GET /api/admin/access-requests` (paginated, filterable by `status` and email/name `search`) and `PATCH /api/admin/access-requests/{id}` (`approved` or `rejected`), or toggle `is_invited` directly via `PATCH /api/admin/users/{id}`. Approving a request links any existing user with that lowercased email and sets `is_invited=True`; rejecting a previously approved request revokes `is_invited` for the linked/matching user while blocking self-revocation and bootstrap-admin revocation. All status and invitation changes emit `AdminAuditEvent` records.

**TODO:** Add the admin review UI and requester outcome UI.

---

## 🏗️ Endpoint Definitions

### 1. Search & Metadata (Public/Auth-Light)

- **`GET /api/search?query=<term>`**: Full-text search for campgrounds and recreation areas (uses the `Search` FTS table).
- **`GET /api/search/explore`**: Paginated search with totals and facets. Optional `west`, `south`, `east`, and `north` filter the full matching set before pagination and aggregation. Supply all four finite bounds or none; longitude is within [-180, 180], latitude within [-90, 90], south < north, and west ≠ east. West > east crosses the antimeridian. Viewport filtering excludes missing/invalid coordinates and lat/lon of 0/0; unbounded search retains unmappable places.
- **`GET /api/providers`**: List supported providers and their scanning capabilities.
- **`GET /api/provider/{id}`**: Get a single provider by ID.
- **`GET /api/campground/{provider}/{id}`**: Get a single campground.
- **`GET /api/rec-area/{provider}/{id}`**: Get a recreation area.
- **`GET /api/rec-area/{provider}/{id}/campgrounds`**: List campgrounds within a recreation area.

### 2. User & Profile (Auth-Required)

- **`GET /api/me`**: Get current user profile, invitation eligibility and `invitation_status`, administrator role, scanning eligibility, and password change status.
- **`PATCH /api/me`**: Update user-specific settings (e.g., `pushover_token`) and return the updated profile including `invitation_status`. Requires password update first if `must_change_password` is set.
- **`POST /api/change-password`**: Update user password and clear `must_change_password` (session mode).

### 3. Scan Management (Auth-Required + Optional Invitation)

- **`GET /api/scans`**: List all scans belonging to the current user (paginated).
- **`POST /api/scans`**: Create a new scan.
  - **Logic**: Backend calculates the target `hash`, creates/links the `UniqueTarget` (de-duplication), and creates the `UserScan`.
  - Returns `201 Created` on success, `409 Conflict` if a duplicate scan exists.
- **`GET /api/scans/{id}`**: Detailed view of a scan, including recent `scan_results`.
- **Result expiration**: User-facing results and `found_count` omit nights before the current UTC date or outside the target interval, then apply the saved minimum stay. This also applies to paused scans. Successful provider checks replace availability, including clearing results for an empty response; failed checks preserve the latest successful snapshot and timestamp.
- **`PATCH /api/scans/{id}`**: Edit the campground/provider, dates, filters (`min_stay_length`, `preferred_types`, `require_electric`), or toggle `is_active`. All fields are optional. Target changes validate the merged date range and campground, then relink only this subscription to a new or existing `UniqueTarget`; shared targets and other subscribers remain unchanged. Duplicate subscriptions return `409`, invalid date ranges return `422`, and unknown campgrounds return `404`. Editing preserves the scan ID, creation date, and active preference unless explicitly changed. Suspended users can edit saved scans, but cannot resume them.
- **`DELETE /api/scans/{id}`**: Unsubscribe from a scan (returns `204 No Content`).

### 4. Administration & Operations (Admin-Only)

- **`GET /api/admin/overview`**: Summary counts (users, active scans, targets, 24h results).
- **`GET /api/admin/users`**: List users with scanning status, scan counts, pagination, and search.
- **`POST /api/admin/users`**: Create a new database user with password, scanning status, admin status, and optional forced password change (session mode only).
- **`GET /api/admin/users/{id}`**: User detail with scans and audit history.
- **`PATCH /api/admin/users/{id}`**: Update scanning access, invitation eligibility (`is_invited`), or administrator role, rejecting self-demotion and revocation of the acting or bootstrap administrator's invitation. Password resets and `must_change_password` updates require session mode; requests containing either field outside session mode return `400` before applying changes. Password resets revoke existing sessions and default to requiring password rotation.
- **`GET /api/admin/access-requests`**: List invitation requests with pagination, `status` filter (`pending`, `approved`, `rejected`), and email/name `search`.
- **`PATCH /api/admin/access-requests/{id}`**: Approve or reject (revoke) an invitation request, recording reviewer metadata, updating linked/matching user `is_invited`, guarding against acting/bootstrap-admin revocation, and recording audit events.
- **`GET /api/admin/scans`**: List all system scans with filters and pagination.
- **`GET /api/admin/scans/{id}`**: Scan detail including target and subscriber info.
- **`PATCH /api/admin/scans/{id}`**: Update scan status (e.g., toggle `is_active`).
- **`GET /api/admin/targets/{id}`**: Shared target detail and subscribers.
- **`GET /api/admin/audit`**: Immutable admin audit event log with pagination.
- **`GET /api/admin/operations`**: Celery worker states, queue depth, discovery metadata, and recent tasks.
- **`GET /api/admin/operations/tasks`**: Paginated Valkey telemetry stream for recent task executions.
- **`GET /api/admin/operations/tasks/{task_id}`**: Detailed telemetry for a single task execution.
- **`GET /api/admin/trends`**: Server-side Prometheus query proxy for `usage`, `api`, `worker`, and `provider` metrics across `24h`, `7d`, `30d`.

---

## 📦 Request / Response DTOs (Pydantic)

All schemas are defined in `src/camply/server/schemas.py`.

### `ScanCreateRequest`

```python
class ScanCreateRequest(BaseModel):
    provider_id: int = Field(..., description="Provider identifier")
    campground_id: str = Field(..., description="Provider-internal campground ID")
    start_date: date = Field(..., description="Check-in date")
    end_date: date = Field(..., description="Check-out date")
    min_stay_length: int = Field(default=1, ge=1)
    preferred_types: list[str] = Field(default_factory=list)
    require_electric: bool = Field(default=False)
```

### `ScanResponse`

```python
class ScanResponse(BaseModel):
    id: UUID
    provider_id: int
    campground_id: str
    campground_name: str
    recreation_area_name: str
    start_date: date
    end_date: date
    is_active: bool
    min_stay_length: int
    preferred_types: list[str]
    require_electric: bool
    last_checked_at: datetime | None
    found_count: int
    created_at: datetime
```

### `ScanDetailResponse` extends `ScanResponse`

Adds:

```python
    results: list[ScanResultItem]
```

### `ScanResultItem`

```python
class ScanResultItem(BaseModel):
    campsite_id: str
    campsite_name: str
    available_dates: list[str]
    campsite_type: str | None
    is_electric: bool | None
    is_accessible: bool | None
    booking_url: str
```

User scan results and `found_count` apply the saved site preferences and minimum consecutive stay. Dates represent available nights in qualifying blocks; check-out is the day after the last night. Booking links are derived from the provider's campground URL without making a provider request. Legacy snapshots have an empty name and unknown attributes until refreshed. Admin shared-target views remain unfiltered.

Scan create/PATCH accept `allowed_weekdays`, a nonempty list of strict integers from 0 (Monday) to 6 (Sunday), normalized by sorting and removing duplicates. Omitted creation values allow all seven; omitted PATCH values preserve the saved preference. Explicit all-seven selection resets to unrestricted, while null, empty lists, booleans, strings, fractions and out-of-range values are invalid. List/detail/create/update responses expose all seven for unrestricted scans, including existing rows. The field belongs to each subscription; shared target identity and duplicate subscription rules stay unchanged.

Creation and edits to dates, nights or minimum stay validate that the merged criteria can contain a qualifying consecutive stay in the remaining date range, before mutation. Impossible combinations return 422 with guidance to change dates, selected nights or length. Provider availability is not part of this validation. Reads, unrelated edits and status-only updates remain possible after expiration. Results and counts exclude disallowed occupied nights before consecutive grouping; checkout itself need not be a selected weekday.

---

## 🔄 Client Generation Workflow

1. Backend developer updates the FastAPI router.
2. Run `task backend:check` to ensure types are correct.
3. Start the backend: `task backend:dev`.
4. Run: `task frontend:codegen` from the repository root.
   - Fetches `http://localhost:8000/api/openapi.json`.
   - Generates TypeScript types in `src/frontend/lib/api/generated/schema.ts`.
5. Register new endpoints in `src/frontend/lib/api.ts` and `src/frontend/lib/structs.ts`.

---

## 🗺️ Endpoint Summary

| Method | Path                                        | Auth      | Invitation (when enabled) | Purpose                              |
| ------ | ------------------------------------------- | --------- | ------------------------- | ------------------------------------ |
| GET    | `/api/search?query=`                        | —         | —                         | Search campgrounds/rec areas         |
| GET    | `/api/providers`                            | —         | —                         | List providers                       |
| GET    | `/api/provider/{id}`                        | —         | —                         | Single provider                      |
| GET    | `/api/campground/{provider}/{id}`           | —         | —                         | Single campground                    |
| GET    | `/api/rec-area/{provider}/{id}`             | —         | —                         | Single rec area                      |
| GET    | `/api/rec-area/{provider}/{id}/campgrounds` | —         | —                         | Campgrounds in rec area              |
| GET    | `/api/me`                                   | ✓         | —                         | Current user profile                 |
| PATCH  | `/api/me`                                   | ✓         | —                         | Update profile                       |
| POST   | `/api/change-password`                      | ✓         | —                         | Change password (session)            |
| GET    | `/api/scans`                                | ✓         | ✓                         | List user scans                      |
| POST   | `/api/scans`                                | ✓         | ✓                         | Create scan                          |
| GET    | `/api/scans/{id}`                           | ✓         | ✓                         | Scan detail                          |
| PATCH  | `/api/scans/{id}`                           | ✓         | ✓                         | Update scan                          |
| DELETE | `/api/scans/{id}`                           | ✓         | ✓                         | Delete scan                          |
| GET    | `/api/health`                               | —         | —                         | Health check                         |
| GET    | `/api/admin/overview`                       | ✓ (Admin) | —                         | Admin KPI overview                   |
| GET    | `/api/admin/users`                          | ✓ (Admin) | —                         | List users with status               |
| POST   | `/api/admin/users`                          | ✓ (Admin) | —                         | Create user with credentials         |
| GET    | `/api/admin/users/{id}`                     | ✓ (Admin) | —                         | User details and audit               |
| PATCH  | `/api/admin/users/{id}`                     | ✓ (Admin) | —                         | Update user (scanning, invite, role) |
| GET    | `/api/admin/access-requests`                | ✓ (Admin) | —                         | List invitation requests             |
| PATCH  | `/api/admin/access-requests/{id}`           | ✓ (Admin) | —                         | Approve or reject access request     |
| GET    | `/api/admin/scans`                          | ✓ (Admin) | —                         | List all system scans                |
| GET    | `/api/admin/scans/{id}`                     | ✓ (Admin) | —                         | Scan detail and target info          |
| PATCH  | `/api/admin/scans/{id}`                     | ✓ (Admin) | —                         | Update scan (toggle active)          |
| GET    | `/api/admin/targets/{id}`                   | ✓ (Admin) | —                         | Shared target detail                 |
| GET    | `/api/admin/audit`                          | ✓ (Admin) | —                         | Immutable audit event log            |
| GET    | `/api/admin/operations`                     | ✓ (Admin) | —                         | Celery worker states & queue         |
| GET    | `/api/admin/operations/tasks`               | ✓ (Admin) | —                         | Valkey telemetry stream              |
| GET    | `/api/admin/operations/tasks/{id}`          | ✓ (Admin) | —                         | Task execution telemetry             |
| POST   | `/api/admin/operations/sync-providers`      | ✓ (Admin) | —                         | Dispatch provider catalog sync       |
| GET    | `/api/admin/trends`                         | ✓ (Admin) | —                         | Prometheus metrics proxy             |

### Admin contract and monitoring availability

Admin frontend types reference the generated OpenAPI schema. Run `task api:generate` after changing response models; `task api:check` verifies drift without starting a server and runs in CI. Overview returns suspended/dormant counts and the actual overdue threshold (cooldown plus two discovery intervals). Scan lists support `target_status=active|overdue|dormant`; target detail uses the same status values.

Operations reports broker connectivity separately from worker inspection and marks incomplete snapshots as stale. Queue/discovery outages preserve prior successful values with explicit availability flags. Task-stream outages return `available=false`, not an empty success. Prometheus outages retain the last successful trend series and timestamp with `available=false`. Celery inspection remains read-only and browser requests only reach FastAPI.

Admin workload fields are nullable: an unanswered or malformed inspection reply is unknown, while a responding worker’s empty task list is a measured zero. Undefined Prometheus samples retain their timestamps with `value: null`, preserving chart gaps and table coverage. Recent task records include an optional `event_id` and one-based `attempt`; older producer records use their Valkey stream ID for row identity and leave the attempt unknown. History readers exclude records older than 24 hours.

### Geographic discovery (public)

`GET /api/search/map/summary` returns global filtered `total`, `mappable_total`, `unmappable_total`, and nullable circular `bounds`. `GET /api/search/map` adds required `west`, `south`, `east`, `north`, and `zoom` (0–19), returning an echoed viewport and at most 512 location/group features. Longitude west > east means an antimeridian crossing; west=-180/east=180 is the full world. Invalid/nonfinite request bounds return 422. Only finite catalog coordinates within ±90/±180 other than lat/lon 0/0 are mapped.

Both routes and `GET /api/search/map/members` reuse the existing Explore predicates, including PostgreSQL fuzzy matching. Map membership ignores list pagination/sort. Groups aggregate every matching visible row in a server-selected geographic grid; singleton features carry the existing search-result metadata. Global counts differ from visible represented counts. Member requests carry `cell_id`, the group's captured viewport, and the same filters, plus `page_size` (default 50, maximum 100) and optional `after_id` (the previous `next_cursor`). This keyset interface keeps co-located places reachable without fetching every list page or transferring the catalog.

These routes expose public catalog metadata and make no campsite-availability claim. Each request reflects the current catalog; no cross-request snapshot is guaranteed during metadata refresh. Existing protected scan endpoints still enforce monitoring access. See the [mapping API contract](../specs/010-open-source-explore-maps/contracts/search-map-api.md). Generate/check types using `task api:generate` and `task api:check`.

## Test notifications

`POST /api/me/notifications/test` accepts the same optional settings fields as `PATCH /api/me`, merged over the authenticated user's current preferences without persistence. It sends one fixed notification and returns `{ "status": "sent", "provider": "ntfy" | "pushover" }` only on explicit upstream acceptance. Missing Pushover user/application credentials return 400/503, a topic claimed by another user returns 409, invalid settings return 422, and sanitized upstream failures return 502. Authentication (401), eligibility/password/invitation restrictions (403), and cookie-session CSRF checks apply. No worker or active scan is required.
