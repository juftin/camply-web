# Feature Implementation Checklist

This checklist tracks the granular progress of `camply`. Agents **MUST** update this file by marking tasks as completed (`[x]`) before finalizing any PR.

---

## 🛠️ Phase 1: Smart Poller & Single-Scan MVP (Current Focus)

### 1.1 Data Layer (`backend/src/camply/db`)

- [x] T1.1.1 Implement `User` model with invitation eligibility (API/model `is_invited`, existing column `is_early_access_user`).
- [x] T1.1.2 Implement `UniqueTarget` model with unique hashing and composite keys.
- [x] T1.1.3 Implement `UserScan` model with user-specific filters.
- [x] T1.1.4 Implement `ScanResult` model for availability caching.
- [x] T1.1.5 Create and run the initial Alembic migration.
- [x] T1.1.6 **Testing**: Write unit tests for models and unique constraint validations.

### 1.2 Provider Engine (`backend/src/camply/providers`)

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
- [x] T1.3.5 Implement the `camply.search.check_campsite_availability` task in Celery.
- [x] T1.3.6 Implement the `camply.notifications.send_pushover_notification` task.
- [x] T1.3.7 Integrate `Sentry` for background task error tracking.
- [x] T1.3.8 **Testing**: Write integration tests for the Celery task lifecycle and de-duplication logic.
- [x] T1.3.9 Configure heartbeat search polling interval to default to 5 minutes (300s) and support customization via `CAMPLY_HEARTBEAT_INTERVAL`.
- [x] T1.3.10 Default to one new-opening summary per saved scan/check linking to Camply results; support configurable individual booking-link alerts for local deployments and preserve unchanged-opening suppression. See [campsite alerts plan](specs/009-campsite-alerts/plan.md).

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
- [x] T1.4.11 **UI Snapshots & Feedback Loop**: Implement automated UI snapshot capture across 40 viewports/routes/themes, visual diffing, and Markdown/HTML reporting (`task snapshot`, `task snapshot:update`, `task snapshot:check`). Automate visual snapshot CI gate with Playwright artifact reporting, enforce deterministic test clocks, and provide comprehensive Vitest component DOM snapshot coverage (31 component test variants).
- [x] T1.4.11a Provide a local HTML comparison gallery linked to before/after PNG files, side-by-side, reveal-slider and diff views, search/status filters, pre-update baseline preservation, report-only regeneration and offline browser verification. See [snapshot gallery plan](specs/010-snapshot-gallery/plan.md).
- [x] T1.4.11b Prevent map snapshot navigation from waiting on background network traffic; wait for search results, rendered maps and loaded markers, with a browser regression covering an indefinitely pending request.
- [x] T1.4.12 Migrate frontend dependency management to pinned pnpm with an imported lockfile; update Task workflows, CI caching, Docker builds, scripts, formatting hooks, and setup documentation.
- [x] T1.4.13 Migrate frontend tooling to Oxlint, Oxfmt, Vite 8, Vitest 5, and native TypeScript 7; align Node 24 across environments and preserve eager page imports.
- [x] T1.4.14 Make plain `task` list available workflows without installing dependencies.
- [x] T1.4.15 Refine DatePicker component and date range synchronization (anchor check-out to check-in, popover calendar, quick duration presets).
- [x] T1.4.16 Add scan editing from dashboard cards and detail pages, safely relink de-duplicated targets, and fix delete navigation, pending state, and failure feedback. Cover form lifecycle, ownership, duplicate validation, and shared-target isolation; see [scan editing plan](specs/006-scan-editing/plan.md).
- [x] T1.4.17 Gate Ethos and Contribute behind `VITE_ENABLE_COMMUNITY_PAGES`, disabled by default; hide related navigation and links, redirect disabled routes home, and document frontend/Docker configuration with regression coverage.
- [x] T1.4.18 Replace placeholder branding with the original camply artwork: horizontal and stacked logos with the title, tent-and-trees artwork without the title, light/dark variants, branded favicons, and the Recreation.gov provider logo. Add the supplied portrait to Meet Justin and preview all logo variations in the design system catalog; see the [branding plan](specs/008-branding/plan.md).
- [x] T1.4.19 Show searchable matching campsite details, consecutive available stays and booking actions; align API/dashboard counts with notification filters, persist provider site attributes, preserve notification destinations through login, and cover desktop/mobile themes. See [campsite alerts plan](specs/009-campsite-alerts/plan.md).
- [x] T1.4.19a Group identical stay dates into collapsible sections with compact campsite rows, unique-site counts, search and date/stay-length sorting; surface scan context and a separate full-campground provider link. Verify grouping and navigation regressions plus desktop/mobile themes.
- [x] T1.4.20 Collapse dashboard scans into campground groups, paginate each stay-date group at five campsites per page, and expire past/out-of-range nights before matching saved stays in the API and alerts. Cover successful availability removal and preservation on provider errors; see [compact results plan](specs/011-compact-results/plan.md).

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
- [x] T2.1.12 Rebuild images on Compose startup and provide local Docker defaults for password sessions, including HTTP cookie settings.
- [x] T2.1.13 Support administrator creation of users and initial passwords in session auth mode, with optional forced password change on first sign-in (`must_change_password`).
- [x] T2.1.14 Enforce forced password change on sign-in across backend APIs and frontend protected/admin routes, allowing users to update their password via `POST /api/change-password`.
- [x] T2.1.15 Allow administrators to promote/demote administrator privileges and reset user passwords with forced rotation on subsequent sign-in via the UI.
- [x] T2.1.16 Revoke previous sessions on password reset/change, refresh the changing browser's cookies, honor stored bootstrap credentials and roles, and restrict password-change flags to session mode; cover these transitions with regression tests.
- [x] T2.1.17 Review and refresh user-management visual baselines for the create/reset actions, password-change status, and administrator role controls; verify all 40 snapshot scenarios.
- [x] T2.1.18 Generate secure random passwords in all admin create/reset dialogs, reveal them while the dialog is open with a copy action, and discard them on close or success; verify lifecycle, clipboard failures, and desktop/mobile/dark visual coverage.

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

### Admin UI ✅

Implementation specification and tasks: [Admin UI plan](specs/002-admin-ui/plan.md).

- [x] Add administrator authorization and scanning suspension while preserving login and saved scan state.
- [x] Build user, scan, and shared-target administration with audited changes.
- [x] Add backend-only, read-only Celery/Valkey visibility and bounded recent task outcomes.
- [x] Add user, scan, lookup-request, and operational trend graphs through backend Prometheus aggregates.
- [x] Replace all relevant Grafana dashboard capabilities with native admin monitoring and remove Grafana deployment/provisioning.
- [x] Build admin frontend routes and verify authorization, suspension, shared targets, and operations outages.
- [x] Integrate current session/invitation authentication and capture deterministic admin screenshots across desktop/mobile and light/dark views.
- [x] Integrate pnpm tooling and local Docker session fixes while preserving scan suspension controls.
- [x] Repair admin contracts, active-target labels, distinct trend series, outage/stale states, mutation feedback/cache refresh, pagination, and shareable investigation filters.
- [x] Generate admin types from OpenAPI and enforce contract drift checks in CI.
- [x] Preserve unknown monitoring values, distinct task attempts and retry outcomes; enforce history retention and add live admin smoke verification in CI.
- [x] Clarify admin scan settings and eligibility, shared-target scan counts, chart units/time zones/legends, and percentile explanations; verify readable charts and tables.
- [x] Update architecture documentation and pass implementation quality gates.
- [x] Add provider metadata synchronization trigger to the Admin Operations UI and CLI (`--provider-id all`).

### 3.1 Migration

- [x] Remove the deprecated `cli/` application after migrating provider functionality to `backend/packages/providers`.
- [ ] T3.1.1 Migrate `usedirect` (California State Parks, etc.).
- [x] T3.1.1a Implement ReserveCalifornia on the current Tyler RDR API: async scans, metadata/search ingestion, seed migration, modern booking links, and synthetic HTTP/database regressions. Source models now share the UseDirect package.
- [x] T3.1.1b Extract the async UseDirect ABC and implement verified Florida, Virginia, Minnesota, Ohio, Arizona, Missouri, Fairfax County, Oregon Metro, and Northern Territory variations with independent metadata sync, stable seeds, booking routes, and provider-isolation regressions.
- [ ] T3.1.1c Discover Alabama State Parks' current catalog/grid endpoints; the legacy catalog returned HTTP 404. See [provider TODOs](specs/005-usedirect-providers/TODO.md).
- [ ] T3.1.1d Discover Maricopa County's current reservation backend and catalog/grid endpoints; the legacy catalog returned HTTP 404. See [provider TODOs](specs/005-usedirect-providers/TODO.md).
- [ ] T3.1.2 Migrate `going_to_camp`.
- [ ] T3.1.3 Migrate `xanterra` (Yellowstone, etc.).

### 3.2 Advanced Search

- [x] T3.2.1 Implement electric hookup and ADA accessibility filters, multi-criteria search, facets, and pagination (`/api/search/explore`, `SearchPage`).
- [x] T3.2.1a Keep discovery in PostgreSQL with indexed weighted full-text and per-token typo matching, exact-name ranking, deterministic pagination, lightweight autocomplete, and live Explore typing/filtering with URL navigation and cancellation. Verify migrations and real PostgreSQL query plans in CI; see [search plan](specs/007-live-search/plan.md).
- [ ] T3.2.1b Populate discovery amenity and RV metadata from provider catalogs; existing imports omit these fields, limiting amenity/RV Explore results.
- [ ] T3.2.2 Implement equipment length (RV/Trailer) validation in poller.
- [ ] T3.2.3 Implement minimum stay requirement (X nights) in poller logic.

### 3.3 Open-Source Maps & Explore Discovery

Feature specification: [Open-Source Maps & Explore Map View](specs/007-open-source-explore-maps/spec.md).

- [x] T3.3.1 Specify replacement of proprietary maps and Explore discovery across all filtered results, including acceptance scenarios and a specification quality checklist.
- [x] T3.3.2 Complete the [technical plan](specs/007-open-source-explore-maps/plan.md), selecting MapLibre GL JS, a keyless OpenStreetMap default, configurable raster sources, and bounded map/group-member contracts.
- [x] T3.3.2a Generate dependency-ordered [implementation tasks](specs/007-open-source-explore-maps/tasks.md) for the mapping plan, including story acceptance checks and live database/browser validation.
- [x] T3.3.3 Replace existing detail maps and add responsive Explore mapping with a collapsible map stacked above the list, filter parity, pagination-independent discovery, and detail/monitor actions.
- [x] T3.3.4 Verify coordinate handling, overlapping/provider-qualified identities, loading and failure recovery, navigation, accessibility, performance, and visual coverage; update mapping setup documentation.
- [x] T3.3.5 Remove the redundant matching-locations/in-view count above Explore's map and refresh visual coverage.
- [x] T3.3.7 Link Explore map zoom/pan to paginated list bounds, initialize unfiltered visits from approximate IP location with fallback, and show hover/focus marker information; see [interaction plan](specs/008-map-list-interaction/plan.md).
- [x] T3.3.8 Refresh Explore list results during continuous map movement, including camera events without DOM metadata; verify with an unreleased browser drag.
- [x] T3.3.9 Wait for a narrowed Explore response when verifying animated zooms, allowing intermediate camera responses while still requiring fewer matching results.
- [ ] T3.3.6 Configure production tile hosting or caching (e.g. MapTiler, Stadia Maps, Cloudflare reverse proxy cache, or self-hosted PMTiles) via `VITE_MAP_*` build variables to adhere to OpenStreetMap's public tile usage policy for high-traffic releases.

---

## 🛠️ Phase 4: Scale, Polish, & Infrastructure

### 4.1 Stability

- [ ] T4.1.1 Implement proxy rotation logic for provider requests.
- [x] T4.1.2 Implement backoff/retry strategy for provider API failures.
- [x] T4.1.3 Setup Prometheus-backed native Admin UI monitoring for scan success metrics (Grafana replaced).

### 4.2 Deployment

- [x] Specify and plan the root project layout, complete frontend-bearing wheel/sdist builds, consolidated Docker/Compose, packaged Gunicorn, nested Pages/Wrangler tooling, and Spec-Kit documentation migration; see [root layout specification](specs/013-root-project-layout/spec.md) and [implementation plan](specs/013-root-project-layout/plan.md).
- [x] Implement and verify [feature 013](specs/013-root-project-layout/plan.md), including the constitution directory amendment and all packaging/deployment/Spec-Kit acceptance checks.

- [x] T4.2.1 Add separate release/publish workflows with CI-gated Gitmoji semantic releases using the shared cookiecutter infrastructure and the existing App through `APP_ID`/`APP_PRIVATE_KEY`, synchronized application build versions, full-version/major-alias GHCR images, latest images for successful main builds, Git major aliases via semantic-release-major-tag, workspace sdists attached to releases, publication regression checks, and [release operations documentation](operations/RELEASES.md); see the [release plan](specs/009-release-ci/plan.md).
- [x] T4.2.2 Specify and plan consolidation into one `camply` Python distribution with internal subpackages and optional runtime extras; see the [package migration plan](specs/012-python-package/plan.md). CLI implementation, local scheduling, UI bundling, and PyPI publication are excluded.
- [x] T4.2.2a Resolve the migration's Python policy (`>=3.11` support; 3.14 development/primary CI/Docker/release defaults), align extras/tooling task order, and add a [requirements and acceptance checklist](specs/012-python-package/checklists/requirements.md).
- [x] T4.2.3 Consolidate workspace members into `backend/src/camply/`, package runtime resources, and update imports, governance, development tooling, containers, and release artifacts.
- [x] T4.2.4 Isolate `server`, `distributed`, `postgres`, and `sentry` extras while keeping providers/SQLite in base and preserving the existing metadata utility.
- [x] T4.2.5 Verify base/server/worker installations and sdist-rebuilt wheels outside the checkout; integrate packaging checks into Task/CI and document migration/deployment limitations.
- [x] T4.2.6 Enforce internal layers, runtime independence, lightweight root imports, and optional dependency boundaries using Import Linter; integrate lint/pre-commit and verify intentional violations fail.
- [x] T4.2.7 Add the `camply.cli` package and base `camply` console script (`--version`/`--help`, `python -m camply.cli`), constrained by Import Linter to base dependencies as a sibling of `server`/`worker`; verify unit, boundary, and isolated-install coverage. Subcommands are future work.
- [x] T4.2.8 Locate installed static assets internally without server dependencies, and serve them with Nginx in one shared `camply-web` image for API, frontend, worker, and beat; unify Compose, release publishing, and CI builds. See the [shared container plan](specs/014-unified-container/plan.md).
- [x] T4.2.9 Tag each shared-image release with `vMAJOR`, `vMAJOR.MINOR.PATCH`, the seven-character release commit SHA, and `latest`.
- [x] T4.2.10 Add `camply serve frontend`, `camply serve backend`, `camply serve worker`, and `camply serve beat`, package Nginx templates with the CLI, and preserve migrations, process signals, and Compose scheduler initialization.
- [x] T4.2.11 Make bare `camply serve` launch the standalone UI/API/SQLite/local scheduler, preserving explicit role subcommands and verifying installed-package HTTP behavior.
- [x] T4.2.12 Check each serving role's dependencies before side effects and launch Python runtimes in the CLI environment; verify missing/partial extras and unrelated `PATH` executables.
- [x] T4.2.13 Preserve required backend/frontend Docker check names with a single shared image build, keeping current branch protection effective.
- [x] T4.2.14 Preserve native serving signals; use graceful Nginx/Python stop signals and a one-minute Compose grace period, with installed HTTP shutdown and forced-termination regression tests.
- [x] T4.2.15 Allow downstream Nginx API upstream overrides through `CAMPLY_BACKEND_URL`, including Compose propagation, installed-package coverage, and proxy routing verification.
- [x] T4.2.16 Gate Compose workers and beat on the migrated API health check; expose opt-in `camply serve beat --sync-providers` with expiring dispatch, startup failure propagation, and CLI/installed-artifact regressions. A fresh PostgreSQL/Valkey smoke verifies post-migration startup ordering and one queued sync.
- [x] T4.2.17 Add `camply serve healthcheck` and backend/frontend/worker/beat probes, with bounded local-worker inspection, scheduler-loop heartbeat freshness/PID checks, Compose adoption, base/installed-package regressions, and live Valkey/worker/beat lifecycle verification in Task/CI.
- [x] T4.2.18 Enable SNI for HTTPS API upstreams; verify real HTTP/TLS proxying with a server that rejects missing SNI, preserve forwarding and frontend health, and run the regression through Task/CI with installed-template coverage.
- [x] T4.2.19 Publish this repository's shared image as `ghcr.io/juftin/camply-web`, retaining release tags/version history and reserving `ghcr.io/juftin/camply` for the future migration; align Compose, publication plans, tests, and documentation.

- [x] T4.2.2 Complete the pre-implementation Spec-Kit specification, clarification review, research, design/contracts, tasking, and consistency analysis for optional Python-served frontend assets, SQLite, and background work without Celery, Redis/Valkey, or Prometheus; see [standalone runtime plan](specs/007-standalone-runtime/plan.md).
- [x] T4.2.3 Implement and verify the standalone runtime, minimal dependency installation, notification recovery, Python-served frontend, and service-free browser smoke tests while preserving the distributed stack; rebase onto current search/maps/results/release behavior and preserve both migration paths. Explicit regressions protect default API startup, Prometheus instrumentation, and Celery scan/alert dispatch from standalone behavior.
- [ ] T4.1.4 Finalize production `docker-compose.yml`.
- [x] T4.1.5 Add the [Camply Helm chart](../deploy/helm/README.md) with scalable API/workers, singleton beat, migration Job startup gates, optional PostgreSQL/Valkey/Prometheus, Ingress/Gateway API routing, configurable/existing PVCs, secret references, stable-release OCI publication as `ghcr.io/juftin/charts/camply-web` with matching image versions, and Task/CI verification; add schema validation, configurable probes with database readiness, ServiceMonitor integration, install notes, Helm connection tests, and source-image lifecycle CI with initialized Task/Python tooling and documented local disk requirements, verified locally through successful and failed upgrades; see the [implementation plan](specs/015-helm-chart/plan.md).
- [ ] T4.1.6 Complete a full mobile-responsive audit of the UI.
