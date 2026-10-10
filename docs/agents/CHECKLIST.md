# Feature Implementation Checklist

This checklist tracks the granular progress of `camply`. Agents **MUST** update this file by marking tasks as completed (`[x]`) before finalizing any PR.

---

## 🛠️ Phase 1: Smart Poller & Single-Scan MVP (Current Focus)

### 1.1 Data Layer (`backend/packages/db`)

- [x] T1.1.1 Implement `User` model with invitation eligibility (API/model `is_invited`, existing column `is_early_access_user`).
- [x] T1.1.2 Implement `UniqueTarget` model with unique hashing and composite keys.
- [x] T1.1.3 Implement `UserScan` model with user-specific filters.
- [x] T1.1.4 Implement `ScanResult` model for availability caching.
- [x] T1.1.5 Create and run the initial Alembic migration.
- [x] T1.1.6 **Testing**: Write unit tests for models and unique constraint validations.

### 1.2 Provider Engine (`backend/packages/providers`)

- [x] T1.2.1 Define the `BaseProvider` ABC with standardized `find_availabilities` and `sync_metadata`.
- [x] T1.2.2 Implement `CampsiteDTO` (Pydantic v2) for unified data transfer.
- [x] T1.2.3 Migrate `recreation_dot_gov` logic from legacy CLI to new structure.
- [x] T1.2.4 Implement the first `sync_metadata` for `recreation_dot_gov` (Facilities/Rec Areas).
- [x] T1.2.5 **Testing**: Write integration tests using `pytest-vcr` for `recreation_dot_gov`.

### 1.3 Celery Worker & Infrastructure

- [x] T1.3.1 Update `docker-compose.yaml` with Valkey and Celery services.
- [x] T1.3.2 Add worker management tasks (`worker:dev`, `worker:beat`) to `backend/Taskfile.yaml`.
- [x] T1.3.3 Setup Celery/Valkey connection in `backend` app.
- [x] T1.3.4 Implement the `heartbeat` (beat) scheduler logic for `unique_targets`.
- [x] T1.3.5 Implement the `check_target_availability` task in Celery.
- [x] T1.3.6 Implement the `send_pushover_notification` task.
- [x] T1.3.7 Integrate `Sentry` for background task error tracking.
- [x] T1.3.8 **Testing**: Write integration tests for the Celery task lifecycle and de-duplication logic.

### 1.4 API & Frontend Foundation

- [x] T1.4.1 Create FastAPI search endpoints (`/api/v1/search`) using existing logic.
- [x] T1.4.2 Create scan management endpoints (`POST /api/v1/scans`, `GET /api/v1/scans`).
- [x] T1.4.3 Refactor existing React frontend to support toggleable Auth0 authentication.
- [x] T1.4.4 Offer owner-selected `none`, in-app `session`, and `auth0` modes independently of the environment; never use HTTP Basic authentication.
- [x] T1.4.5 Setup automated OpenAPI TypeScript client generation and TanStack Query.
- [x] T1.4.6 Implement the `Dashboard` page (`/dashboard`) for scan management.
- [x] T1.4.7 Build the `ScanForm` component using Shadcn/UI and React Hook Form.
- [x] T1.4.8 Connect the existing `SearchBar` to the `ScanForm` flow.
- [x] T1.4.9 Implement the optional invite-only gate UI.
- [x] T1.4.10 **Testing**: Write backend API tests (`pytest`) and frontend component tests (`vitest`). _(✅ 16 backend + 13 frontend tests passing)_
- [x] T1.4.11 **UI Snapshots & Feedback Loop**: Implement automated UI snapshot capture, visual diffing, and Markdown/HTML reporting (`task snapshot`, `task snapshot:update`, `task snapshot:check`).
- [x] T1.4.12 Migrate frontend dependency management to pinned pnpm with an imported lockfile; update Task workflows, CI caching, Docker builds, scripts, formatting hooks, and setup documentation.
- [x] T1.4.13 Migrate frontend tooling to Oxlint, Oxfmt, Vite 8, Vitest 5, and native TypeScript 7; align Node 24 across environments and preserve eager page imports.
- [x] T1.4.14 Make plain `task` list available workflows without installing dependencies.

### 1.5 Governance & Licensing

- [x] T1.5.1 Research and select a Non-Commercial license (Polyform Noncommercial 1.0.0).
- [x] T1.5.2 Update `LICENSE` file and repository headers to reflect new terms.

---

## 🛠️ Phase 2: Auth0 & Optional Invite-Only Access

### 2.1 Authentication & Profile

- [x] T2.1.1 Configure Auth0 backend integration (JWT validation).
- [x] T2.1.2 Enforce optional invitation eligibility on every scan endpoint.
- [x] T2.1.3 Configure Auth0 frontend integration with the backend API audience and mode-aware signup.
- [x] T2.1.4 Build the User Profile page for Pushover key management.
- [x] T2.1.7 Add in-app shared-account login/logout with signed, expiring HTTP-only cookies and CSRF protection; remove Basic credentials, challenges, and configuration.
- [x] T2.1.8 Verify auth navigation and Auth0 callback URLs with both root and repository-subpath base URLs, including the GitHub CI environment.
- [x] T2.1.9 Confirm the browser session after password login before opening the dashboard; avoid retrying scan requests denied with 401/403 and clear cached session/scan data on a scan query's 401 to return to sign-in.
- [x] T2.1.10 Verify scan session authentication over secure HTTPS; add a Cloudflare Pages `/api` proxy preserving session/CSRF cookies, with transport regressions and deployment instructions for cross-site backends.
- [x] T2.1.11 Trust HTTPS deployment-hash and branch-alias origins for the camply Cloudflare Pages project in CORS and password login; test rejection of unrelated projects and lookalike domains.

### 2.2 Access Control

- [x] T2.1.5 Gate dashboard and scan-detail routes for uninvited users when invite-only access is enabled.
- [x] T2.1.6 Collect pending invitation requests (email collection only).
- [ ] TODO: Add invitation approval/revocation and safe matching to verified identities.
- [ ] TODO: Deliver invitation notifications; request collection currently sends no email.

### 2.3 Email & Account Linking

- [ ] T2.3.1 Define trusted email provisioning (verified Auth0 claims or server-side profile retrieval); keep the identity subject separate from the email address.
- [ ] T2.3.2 Synchronize verified email changes without losing invitation eligibility, scans, or notification preferences.
- [ ] T2.3.3 Define explicit account-linking rules that require proof of ownership; do not automatically merge identities solely because their emails match.
- [ ] T2.3.4 Handle duplicate-email conflicts and concurrent provisioning without server errors; test missing/unverified emails, email changes, and multiple identities sharing an email.

### 2.4 Token Expiry & Session Recovery

- [ ] T2.4.1 Surface token acquisition failures and distinguish expired sessions, authentication failures, and temporary identity-provider outages.
- [ ] T2.4.2 Define bounded renewal/retry behavior for expired tokens and require sign-in when renewal is unavailable; prevent redirect/retry loops and automatic replay of unsafe mutations.
- [ ] T2.4.3 Test Auth0 expiry during an active session, renewal success/failure, revoked sessions, and account switching; verify protected queries wait for authentication and user caches clear on logout.

### 2.5 Token Storage

- [x] T2.5.0 Use HTTP-only signed cookies for in-app password sessions; test expiry, tampering, CSRF, cookie flags, and invalidation after credential changes.
- [ ] T2.5.1 Review Auth0 browser token storage and choose between SDK memory storage and server-managed sessions; document refresh persistence and browser compatibility tradeoffs.
- [ ] T2.5.2 Implement the chosen storage strategy, including token lifetime/renewal settings and, if cookies are used, secure cookie attributes and CSRF protection.
- [ ] T2.5.3 Test page reloads, multiple tabs, logout, and session expiry; verify credentials/tokens do not appear in application logs or unintended persistent storage.

- [ ] T2.5.4 Add individual server-side revocation for password sessions; current signed cookies remain valid until expiry or credential/secret rotation.

### 2.6 Signed JWT Verification Tests

- [ ] T2.6.1 Generate synthetic RSA keys and signed JWTs in tests; exercise the real verifier while mocking only JWKS transport, without live Auth0 credentials.
- [ ] T2.6.2 Explicitly require expiration and a nonempty subject; test valid tokens, expired tokens, missing claims, incorrect issuer/audience, tampered signatures, and disallowed algorithms.
- [ ] T2.6.3 Test JWKS caching, key rotation, unknown key IDs, and JWKS outages; distinguish invalid credentials from temporary verification-service failures.
- [ ] T2.6.4 Exercise signed-token API requests to verify user provisioning, scan ownership isolation, and optional invitation enforcement.

---

## 🛠️ Phase 3: Provider Parity & Advanced Features

### 3.1 Migration

- [ ] T3.1.1 Migrate `usedirect` (California State Parks, etc.).
- [ ] T3.1.2 Migrate `going_to_camp`.
- [ ] T3.1.3 Migrate `xanterra` (Yellowstone, etc.).

### 3.2 Advanced Search

- [ ] T3.2.1 Implement electric hookup and ADA accessibility filters.
- [ ] T3.2.2 Implement equipment length (RV/Trailer) validation in poller.
- [ ] T3.2.3 Implement minimum stay requirement (X nights) in poller logic.

---

## 🛠️ Phase 4: Scale, Polish, & Infrastructure

### 4.1 Stability

- [ ] T4.1.1 Implement proxy rotation logic for provider requests.
- [x] T4.1.2 Implement backoff/retry strategy for provider API failures.
- [x] T4.1.3 Setup Prometheus/Grafana dashboard for scan success metrics.

### 4.2 Deployment

- [ ] T4.1.4 Finalize production `docker-compose.yml`.
- [ ] T4.1.5 Create Kubernetes manifests for API and Worker scaling.
- [ ] T4.1.6 Complete a full mobile-responsive audit of the UI.
