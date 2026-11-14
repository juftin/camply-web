# Feature Implementation Checklist

This checklist tracks the granular progress of `camply`. Agents **MUST** update this file by marking tasks as completed (`[x]`) before finalizing any PR.

## Legacy CLI parity (026)

- [x] Audit legacy `juftin/camply` v0.34.4 CLI commands, options, YAML/configuration, providers, deployment IDs and notifications; map replacements and gaps in the [baseline inventory](specs/026-cli-parity/legacy-audit.md).
- [x] Write the [parity specification](specs/026-cli-parity/spec.md), [design outline](specs/026-cli-parity/plan.md), [delivery backlog](specs/026-cli-parity/tasks.md) and [readiness checklist](specs/026-cli-parity/checklists/requirements.md).
- [x] Narrow initial CLI scope and track D01–D13 as [deferred TODOs](specs/026-cli-parity/tasks.md#deferred-todo-registry), including site listing/selection, full notification/campground parity, YAML, permits, equipment, TUI, Rich-click, configure, notification caps and offline history.
- [x] Address command-contract and test-coverage review gaps: specify option precedence/repeatability, exact campground lookup and real installed-command monitoring/cancellation acceptance gates. Keep initial CLI output console-only; defer Pushover and all external notification setup/delivery.
- [x] Restore current-provider discovery and campground-based availability through shared base-only capabilities: exact metadata lookup, complete area expansion, paired date/day matching, continuous console output and cancellation cleanup.
- [x] Verify initial CLI acceptance with full test/lint/type/docs gates and installed wheel/sdist checks on Python 3.11/3.14; keep all D01–D13 deferred.
- [x] Separate CLI commands/groups into dedicated modules, centralize reusable options and share discovery/output/execution helpers while preserving lazy imports and command behavior.
- [x] Add `camply` v1-style Rich CLI logging (`CAMPLY` log level, welcome/exit banners, debug diagnostics, `CAMPLY_LOG_HANDLER=python` fallback, and stdout/stderr stream separation), log provider/discovery/availability results in classic `camply` emoji hierarchy (`⛰`, `🏕`, `📅`, `🔗`) without truncation, and verify CLI terminal screenshots in Chromium and `pytest`.
- [x] Stabilize snapshot capture by waiting for visible image/font readiness, cover delayed lazy-image loading without network-idle waits, and refresh the complete desktop light profile baseline from macOS CI.
- [ ] Brainstorm CLI lifecycle and `--continuous` / `--search-forever` / `--search-once`; intended default is search forever. Deferred TODO implementation is outside the initial release gate.

## Destination enrichment research (027)

- [x] Audit retained metadata and verify upstream enrichment sources; document Recreation.gov export/media and California park-information evidence, access limitations, and a [phased implementation proposal](specs/027-campground-enrichment/plan.md).
- [x] Expand the [provider research matrix](specs/027-campground-enrichment/provider-matrix.md) across all ten UseDirect deployments, verified ReserveAmerica galleries/details, and Washington's official operator-site gallery; identify placeholder URLs, missing assets, photo scope, and remaining native GoingToCamp access limits.
- [x] Implement cached destination photos and practical details for Recreation.gov, all ten UseDirect deployments, and ReserveAmerica; add portable JSON persistence/migration, bounded seven-day refreshes with failure retention and retry continuation, detail-only API responses, accessible galleries, provenance, synthetic regressions, and enriched visual baselines. See the [feature plan](specs/027-campground-enrichment/plan.md).

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
- [x] T1.3.10 Default to one new-opening summary per saved scan/check linking to Camply results; support configurable individual booking-link alerts for local deployments and preserve unchanged-opening suppression. See [campsite alerts plan](specs/014-campsite-alerts/plan.md).

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
- [x] T1.4.11a Provide a local HTML comparison gallery linked to before/after PNG files, side-by-side, reveal-slider and diff views, search/status filters, pre-update baseline preservation, report-only regeneration and offline browser verification. See [snapshot gallery plan](specs/016-snapshot-gallery/plan.md).
- [x] T1.4.11b Prevent map snapshot navigation from waiting on background network traffic; wait for search results, rendered maps and loaded markers, with a browser regression covering an indefinitely pending request.
- [x] T1.4.11c Improve visual regression and DOM snapshot determinism: enforce UTC timezone in test setup, and pin US English locale and device scale factor in browser context.
- [x] T1.4.11d Accelerate UI snapshot execution with parallel worker concurrency, scenario filtering (`--filter`), DOM-mount navigation without `networkidle` pauses, isolated default port (`5197`), and clean process-group shutdown.
- [x] T1.4.12 Migrate frontend dependency management to pinned pnpm with an imported lockfile; update Task workflows, CI caching, Docker builds, scripts, formatting hooks, and setup documentation.
- [x] T1.4.13 Migrate frontend tooling to Oxlint, Oxfmt, Vite 8, Vitest 5, and native TypeScript 7; align Node 24 across environments and preserve eager page imports.
- [x] T1.4.14 Make plain `task` list available workflows without installing dependencies.
- [x] T1.4.15 Refine DatePicker component and date range synchronization (anchor check-out to check-in, popover calendar, quick duration presets).
- [x] T1.4.16 Add scan editing from dashboard cards and detail pages, safely relink de-duplicated targets, and fix delete navigation, pending state, and failure feedback. Cover form lifecycle, ownership, duplicate validation, and shared-target isolation; see [scan editing plan](specs/008-scan-editing/plan.md).
- [x] T1.4.17 Gate Ethos and Contribute behind `VITE_ENABLE_COMMUNITY_PAGES`, disabled by default; hide related navigation and links, redirect disabled routes home, and document frontend/Docker configuration with regression coverage.
- [x] T1.4.18 Replace placeholder branding with the original camply artwork: horizontal and stacked logos with the title, tent-and-trees artwork without the title, light/dark variants, branded favicons, and the Recreation.gov provider logo. Add the supplied portrait to Meet Justin and preview all logo variations in the design system catalog; see the [branding plan](specs/012-branding/plan.md).
- [x] T1.4.19 Show searchable matching campsite details, consecutive available stays and booking actions; align API/dashboard counts with notification filters, persist provider site attributes, preserve notification destinations through login, and cover desktop/mobile themes. See [campsite alerts plan](specs/014-campsite-alerts/plan.md).
- [x] T1.4.19a Group identical stay dates into collapsible sections with compact campsite rows, unique-site counts, search and date/stay-length sorting; surface scan context and a separate full-campground provider link. Verify grouping and navigation regressions plus desktop/mobile themes.
- [x] T1.4.20 Collapse dashboard scans into campground groups, paginate each stay-date group at five campsites per page, and expire past/out-of-range nights before matching saved stays in the API and alerts. Cover successful availability removal and preservation on provider errors; see [compact results plan](specs/017-compact-results/plan.md).

### 1.5 Governance & Licensing

- [x] T1.5.1 Research and select an open-source copyleft license (GNU AGPLv3).
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
- [ ] T3.1.1c Discover Alabama State Parks' current catalog/grid endpoints; the legacy catalog returned HTTP 404. See [provider TODOs](specs/007-usedirect-providers/TODO.md).
- [ ] T3.1.1d Discover Maricopa County's current reservation backend and catalog/grid endpoints; the legacy catalog returned HTTP 404. See [provider TODOs](specs/007-usedirect-providers/TODO.md).
- [ ] T3.1.2 Migrate `going_to_camp`.
- [x] T3.1.2a Re-engineer the async `GoingToCampProvider` ABC (dynamic nightly booking/resource categories, bulk resource metadata, 60-night map availability BFS traversal, multi-category equipment and filterable attribute decoding) and implement `WashingtonStateParksProvider` (`https://washington.goingtocamp.com`, ID 12) with seed migration, deep links, and synthetic HTTP/VCR/database regressions. See [GoingToCamp plan](specs/023-going-to-camp/plan.md) and [remaining deployment TODOs](specs/023-going-to-camp/TODO.md).
- [ ] T3.1.3 Migrate `xanterra` (Yellowstone, etc.).

### 3.2 Advanced Search

- [x] T3.2.1 Implement electric hookup and ADA accessibility filters, multi-criteria search, facets, and pagination (`/api/search/explore`, `SearchPage`).
- [x] T3.2.1a Keep discovery in PostgreSQL with indexed weighted full-text and per-token typo matching, exact-name ranking, deterministic pagination, lightweight autocomplete, and live Explore typing/filtering with URL navigation and cancellation. Verify migrations and real PostgreSQL query plans in CI; see [search plan](specs/009-live-search/plan.md).
- [ ] T3.2.1b Populate discovery amenity and RV metadata from provider catalogs; existing imports omit these fields, limiting amenity/RV Explore results.
- [ ] T3.2.2 Implement equipment length (RV/Trailer) validation in poller.
- [ ] T3.2.3 Implement minimum stay requirement (X nights) in poller logic.

### 3.3 Open-Source Maps & Explore Discovery

Feature specification: [Open-Source Maps & Explore Map View](specs/010-open-source-explore-maps/spec.md).

- [x] T3.3.1 Specify replacement of proprietary maps and Explore discovery across all filtered results, including acceptance scenarios and a specification quality checklist.
- [x] T3.3.2 Complete the [technical plan](specs/010-open-source-explore-maps/plan.md), selecting MapLibre GL JS, a keyless OpenStreetMap default, configurable raster sources, and bounded map/group-member contracts.
- [x] T3.3.2a Generate dependency-ordered [implementation tasks](specs/010-open-source-explore-maps/tasks.md) for the mapping plan, including story acceptance checks and live database/browser validation.
- [x] T3.3.3 Replace existing detail maps and add responsive Explore mapping with a collapsible map stacked above the list, filter parity, pagination-independent discovery, and detail/monitor actions.
- [x] T3.3.4 Verify coordinate handling, overlapping/provider-qualified identities, loading and failure recovery, navigation, accessibility, performance, and visual coverage; update mapping setup documentation.
- [x] T3.3.5 Remove the redundant matching-locations/in-view count above Explore's map and refresh visual coverage.
- [x] T3.3.7 Link Explore map zoom/pan to paginated list bounds, initialize unfiltered visits from approximate IP location with fallback, and show hover/focus marker information; see [interaction plan](specs/013-map-list-interaction/plan.md).
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

- [x] Specify and plan the root project layout, complete frontend-bearing wheel/sdist builds, consolidated Docker/Compose, packaged Gunicorn, nested Pages/Wrangler tooling, and Spec-Kit documentation migration; see [root layout specification](specs/019-root-project-layout/spec.md) and [implementation plan](specs/019-root-project-layout/plan.md).
- [x] Implement and verify [feature 013](specs/019-root-project-layout/plan.md), including the constitution directory amendment and all packaging/deployment/Spec-Kit acceptance checks.

- [x] T4.2.1 Add separate release/publish workflows with CI-gated Gitmoji semantic releases using the shared cookiecutter infrastructure and the existing App through `APP_ID`/`APP_PRIVATE_KEY`, synchronized application build versions, full-version/major-alias GHCR images, latest images for successful main builds, Git major aliases via semantic-release-major-tag, workspace sdists attached to releases, publication regression checks, and [release operations documentation](operations/RELEASES.md); see the [release plan](specs/015-release-ci/plan.md).
- [x] T4.2.2 Specify and plan consolidation into one `camply` Python distribution with internal subpackages and optional runtime extras; see the [package migration plan](specs/018-python-package/plan.md). CLI implementation, local scheduling, UI bundling, and PyPI publication are excluded.
- [x] T4.2.2a Resolve the migration's Python policy (`>=3.11` support; 3.14 development/primary CI/Docker/release defaults), align extras/tooling task order, and add a [requirements and acceptance checklist](specs/018-python-package/checklists/requirements.md).
- [x] T4.2.3 Consolidate workspace members into `backend/src/camply/`, package runtime resources, and update imports, governance, development tooling, containers, and release artifacts.
- [x] T4.2.4 Isolate `server`, `distributed`, `postgres`, and `sentry` extras while keeping providers/SQLite in base and preserving the existing metadata utility.
- [x] T4.2.5 Verify base/server/worker installations and sdist-rebuilt wheels outside the checkout; integrate packaging checks into Task/CI and document migration/deployment limitations.
- [x] T4.2.6 Enforce internal layers, runtime independence, lightweight root imports, and optional dependency boundaries using Import Linter; integrate lint/pre-commit and verify intentional violations fail.
- [x] T4.2.7 Add the `camply.cli` package and base `camply` console script (`--version`/`--help`, `python -m camply.cli`), constrained by Import Linter to base dependencies as a sibling of `server`/`worker`; verify unit, boundary, and isolated-install coverage. Subcommands are future work.
- [x] T4.2.8 Locate installed static assets internally without server dependencies, and serve them with Nginx in one shared `camply-web` image for API, frontend, worker, and beat; unify Compose, release publishing, and CI builds. See the [shared container plan](specs/020-unified-container/plan.md).
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
- [x] T4.2.20 Modularize Taskfile into domain-specific taskfiles (`tasks/{compose,helm,release,standalone}.yaml`), curate default `task` listing down to primary developer workflows using `summary:` and `internal: true` for CI/niche tasks, add granular `check:format`, `check:lint`, and `check:types` tasks, and re-work GitHub Actions CI, release, and publish workflows and composite setup actions with standardized `<domain> - <action>` job/step conventions, idempotent task installations, and validated task dependencies.
- [x] T4.2.21 Publish the standalone Python package distribution as `camply-web` on PyPI upon release, configuring PyPI Trusted Publishing and aligning build scripts, package metadata, Taskfile targets, and CI publish workflows.
- [x] T4.2.22 Pin Python application and optional dependencies to exact versions and configure uv wheel-only binary resolution (`environments`, `required-environments`, and `no-build`) for Python 3.11–3.15 across Linux, macOS, and Windows.

- [x] T4.2.2 Complete the pre-implementation Spec-Kit specification, clarification review, research, design/contracts, tasking, and consistency analysis for optional Python-served frontend assets, SQLite, and background work without Celery, Redis/Valkey, or Prometheus; see [standalone runtime plan](specs/011-standalone-runtime/plan.md).
- [x] T4.2.3 Implement and verify the standalone runtime, minimal dependency installation, notification recovery, Python-served frontend, and service-free browser smoke tests while preserving the distributed stack; rebase onto current search/maps/results/release behavior and preserve both migration paths. Explicit regressions protect default API startup, Prometheus instrumentation, and Celery scan/alert dispatch from standalone behavior.
- [ ] T4.1.4 Finalize production `docker-compose.yml`.
- [x] T4.1.5 Add the [Camply Helm chart](https://github.com/juftin/camply-web/blob/main/deploy/helm/README.md) with scalable API/workers, singleton beat, migration Job startup gates, optional PostgreSQL/Valkey/Prometheus, Ingress/Gateway API routing, configurable/existing PVCs, secret references, stable-release OCI publication as `ghcr.io/juftin/charts/camply-web` with matching image versions, and Task/CI verification; add schema validation, configurable probes with database readiness, ServiceMonitor integration, install notes, Helm connection tests, and source-image lifecycle CI with initialized Task/Python tooling and documented local disk requirements, verified locally through successful/failed upgrades and rollback, with database-backed migration checkpoints and Prometheus configuration rollouts; see the [implementation plan](specs/021-helm-chart/plan.md).
- [x] T4.1.5a Render explicit HTTPRoute backend reference defaults (`group`, `kind`, and `weight`) to prevent ArgoCD drift, with Gateway and home-ops rendering regressions.
- [x] T4.1.5b Publish Helm OCI chart tags `vMAJOR`, `vMAJOR.MINOR.PATCH`, seven-character SHA, and `latest`, each selecting the matching upstream image tag; include SHA/latest images and charts on successful main builds, retain unprefixed release compatibility, and verify Helm 3/4 OCI installs by digest.
- [ ] T4.1.6 Complete a full mobile-responsive audit of the UI.

### Documentation

- [x] Simplify the README around camply, the hosted app, local setup, and links to further documentation; preserve the runtime and packaging reference in [Running camply](operations/RUNNING.md).
- [x] Add a VitePress site under `docs/site`, with usage, standalone, container hosting, configuration, development, and reference guides; provide `task docs:install`, `task docs:serve`, `task docs:build`, and `task docs:check`. Verify the build, generated links/assets, and local HTTP preview; see the [documentation plan](specs/022-documentation-site/plan.md).
- [x] Follow cookiecutter-python's shared GitHub Pages action to publish `build/docs` after successful main CI, validate docs on PRs, configure the canonical site URL, and document one-time Pages enablement; add publishing-boundary/link regressions and retain the new Task include in release fixtures.
- [x] Use `uvx --from "camply-web[server]" camply serve` for user setup, remove the standalone `populate-database` script in favor of `camply db metadata`, add `camply db info`, `camply db migrate`, and `camply db delete`, and align PyPI package and GitHub repository references.
- [x] Build documentation into every frontend bundle at `/docs/`, link it from the app footer, manage VitePress via `package.json`, and preserve docs sources/assets in wheel/sdist integrity checks. Serve documentation pages and real documentation 404s in Python, Nginx, and Cloudflare Pages previews; verify installed artifacts without the generator.
- [x] Eliminate Python documentation build dependencies from frontend builds, Dockerfile frontend stage, and Cloudflare Pages, ensure unprivileged Nginx smoke environments run with proper file permissions, and maintain baseline visual snapshots for the footer docs link.
- [x] Re-organize documentation site directly under `docs/`, natively representing all operations, architecture, development, roadmap, checklist, and feature specification documents without duplicate files or copy scripts.

- [x] GoingToCamp review follow-up: decode scalar enum attributes, verify PostgreSQL provider seed upgrade expectations, and disclose provider booking restrictions in results.

### ntfy notifications

- [x] Assign each account an editable ntfy topic defaulting to `camply-` plus the first seven user-ID characters, including migration of existing users.
- [x] Add per-user provider selection and Profile settings for custom HTTP(S) servers and optional access tokens.
- [x] Deliver through the selected Pushover or ntfy provider in standalone and distributed runtimes.
- [x] Test publishing, settings validation, delivery eligibility, provider switching and retries. See [ntfy plan](specs/024-ntfy/plan.md).

- [x] Configure default ntfy publish/subscription URLs server-side, expose only public subscriptions, and support per-user custom servers and publish URL fallback.

- [x] Offer a Profile dropdown for the configured ntfy server (when set), ntfy.sh or a user-provided server URL.

- [x] Switch provider settings immediately and generate editable ntfy topics using `camply-` plus the first seven user-ID characters, with topic validation and migration coverage.

- [x] Default editable ntfy topics to `camply-<first seven user-ID characters>` and migrate earlier generated defaults.

- [x] Copy current ntfy server and topic from Profile, with accessible clipboard feedback and disabled empty-value copying.

- [x] Send a test notification from Profile using unsaved provider settings, with explicit acceptance, API-only delivery, eligibility/CSRF checks and safe failure feedback.

- [x] Remove the redundant Subscription URL section from Profile while retaining server/topic controls and copying.

- [x] Resolve notification review findings: clear tokens when switching servers, preserve private publishing defaults with ntfy.sh subscriptions, recover generated-topic collisions in every account-creation flow, tie save feedback to submitted values, and explain subscribing before testing.
- [x] Integrate current provider/CLI changes, join deployed ntfy and provider migration histories, and cover ntfy settings in desktop/mobile visual checks.

### ReserveAmerica provider

- [x] Register ReserveAmerica (ID 13), guarded seed migration, and contract-scoped campground/site IDs; update installed-artifact and PostgreSQL smoke provider expectations.
- [x] Discover native US overnight campgrounds from bulk brand metadata and paginated state searches; refresh metadata/search atomically.
- [x] Scan paginated site grids in 14-night windows, map explicit campsite attributes, and preserve failures for worker retry.
- [x] Keep auth headers aligned with rotated, deleted and expired cookies; recover after unsuccessful refreshes and serialize concurrent callers.
- [x] Cover synthetic HTTP, persistence, migration and registry regressions; verify live CO metadata and site scanning. See [endpoint research](specs/024-reserve-america/validation.md).

- [x] Replace Yellowstone Lodges with ReserveAmerica in popular/all provider cards.
- [x] Update provider-page visual baselines from inspected macOS CI captures.

- [x] Use `www.reserveamerica.com` for public links, retain the separate `a1` API/session URLs, and migrate existing seeded provider URLs with custom-URL preservation.

### Direct provider search (025)

- [x] Add validated database-independent upstream campground and recreation-area search with typed results.
- [x] Implement Recreation.gov, shared UseDirect regional providers, GoingToCamp, and ReserveAmerica search.
- [x] Cover all registered providers with synthetic HTTP eligibility, entity selection, filter, validation, and failure tests.
- [x] Use `SearchEntityType` string enums or plain strings; default to `None` for all types and reject `"both"`.
- [x] Preserve entities with coinciding park/campground IDs and avoid facility requests for area-only discovery.
- [x] Resolve independent review findings for Recreation.gov parent-scoped requests and District of Columbia state normalization.
- [x] Document future CLI consumption; keep web search and CLI commands unchanged.
- [x] Pass full test and quality workflows, including a final backend rerun after independent-review fixes.
- [x] Keep provider extension methods public: `search_upstream` is the abstract discovery contract.

### Dependency Maintenance

- [x] Consolidate verified Renovate dependency upgrades into a single release PR, excluding risky or incompatible upgrades (Python 3.15, Postgres 18, React 19, Tailwind CSS v4, TypeScript 7, Lucide React 1.x, @types/node 26, and major Redis/Hookform bumps).
