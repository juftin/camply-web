# Feature Specification: Optional standalone runtime

**Feature Branch**: `rare-mole`
**Created**: 2026-10-13
**Status**: Ready for implementation review; implementation not started
**Input**: Optionally run camply with Python and TypeScript, served entirely by Python, using SQLite without PostgreSQL, Prometheus, Celery, or Redis/Valkey. Complete Spec-Kit planning and stop before implementation.

## User Scenarios & Testing

### User Story 1 - Start the application without services (Priority: P1)

An owner runs the complete application on a personal computer or small server, using local storage and one website/API address.

**Why this priority**: A usable deployment must not require separate database, worker, broker, or monitoring services.

**Independent Test**: Start a prepared installation with backing services absent, open the website and a saved deep link, save user/scan state, restart, and verify that state remains.

**Acceptance Scenarios**:

1. **Given** built assets and fresh writable storage, **when** standalone starts, **then** storage is initialized/upgraded and the website and API are available at one origin without excluded services.
2. **Given** an installed application, **when** a user refreshes a dashboard/admin deep link, **then** the website loads; missing API routes and assets produce genuine errors.
3. **Given** missing assets, unwritable storage, an unsupported database, or conflicting worker settings, **when** startup is attempted, **then** it fails with a corrective message before serving.
4. **Given** saved users, scans, preferences, results, and pending alerts, **when** the app restarts or storage is backed up/restored, **then** those records remain usable without the source checkout or frontend build tools.

### User Story 2 - Discover and monitor campsites (Priority: P1)

An owner populates catalogs, creates scans, and receives matching alerts without separate worker processes.

**Why this priority**: The new deployment must perform the campsite finder's core work.

**Independent Test**: Use synthetic providers and notification transports to refresh catalogs, create two subscriptions sharing a target, observe one check and individually filtered alerts, then exercise interruption and recovery.

**Acceptance Scenarios**:

1. **Given** an empty catalog, **when** an administrator requests sync, **then** the request returns promptly, progress/failures are visible, and metadata becomes searchable without availability selections. Daily refresh also runs.
2. **Given** two eligible subscriptions sharing one target, **when** a check is due, **then** one provider check serves both and alerts match individual filters.
3. **Given** paused, suspended, deleted, or edited subscriptions, **when** work executes or alerts send, **then** current ownership, eligibility, target association, dates, filters, and preferences control delivery.
4. **Given** provider failure, **when** work retries, **then** previous results remain intact, checks do not overlap, and other targets/HTTP requests proceed.
5. **Given** a committed detection, **when** the process stops before delivery, **then** the pending alert survives restart and retries within its limit. A crash after external acceptance may cause a duplicate. Closing and reopening is a new detection.

### User Story 3 - Operate either deployment mode (Priority: P2)

Administrators understand runtime health and manage users/scans without intentionally absent monitoring appearing broken.

**Why this priority**: Local health must be honest and the existing distributed deployment must remain supported.

**Independent Test**: Exercise administration/status/catalog sync in both modes; verify disabled features are distinct from actual failures.

**Acceptance Scenarios**:

1. **Given** standalone, **when** operations opens, **then** scheduler health, discovery, running work, sync status, and recent outcomes appear; broker panels and historical charts are hidden with an explanation.
2. **Given** local recent history, **when** records exceed 1,000 or 24 hours, **then** old records are removed; the UI explains that history clears on restart while pending alert state survives.
3. **Given** disabled trends, **when** a client requests them directly, **then** it receives intentional unavailability without an external query. A failed runner instead reports unhealthy status.
4. **Given** distributed mode, **when** current workflows run, **then** workers, broker inspection, metrics, trends, separate frontend hosting, and admin controls remain supported.

### Edge Cases

- Slow catalogs/provider requests do not block HTTP or alert delivery. Repeated sync requests share an active job; one failed provider does not stop others.
- Deleted, relinked, expired, or newly nonmatching scans are skipped before delivery.
- Transient failures retry finitely; malformed payloads/missing credentials produce terminal outcomes.
- A failed result transaction creates neither partial results nor delivery intents. Accepted external delivery followed by a crash can duplicate an alert.
- Multiple subscriptions share checks; multiple app instances sharing one database are unsupported.
- Unknown work values remain unknown; disabled features are not reported as outages.
- Static routes and operational history cannot expose credentials or database/repository files.

## Requirements

### Functional Requirements

- **FR-001**: Owners MUST select standalone/distributed independently of auth/environment; distributed remains default.
- **FR-002**: Standalone MUST serve built frontend/API at one origin, support deep links, and retain genuine asset/API errors.
- **FR-003**: File-backed SQLite MUST support fresh initialization, populated upgrades, persistence, and backup/restore of all saved state and pending alerts.
- **FR-004**: Runtimes MUST share discovery/provider/comparison/filter/eligibility/notification behavior rather than duplicate the scanner.
- **FR-005**: Standalone MUST provide bounded, supervised polling, daily sync, delivery, finite retry/backoff, and graceful shutdown without overlapping target checks.
- **FR-006**: Standalone MUST commit notification intents atomically with results, recover pending delivery, document at-least-once semantics, and allow a new reopening alert.
- **FR-007**: Standalone MUST install/start without Celery, Redis, Prometheus client, or PostgreSQL driver libraries and without contacting those services.
- **FR-008**: Both runtimes MUST retain auth, CSRF, invitations, authorization, ownership, preferences, and admin controls; standalone pending alerts MUST recheck current eligibility/filters.
- **FR-009**: Administration MUST expose capabilities and local status/history with finite retention, distinguishing unsupported, unknown, empty, and failed states.
- **FR-010**: Documented Task workflows MUST install/build/launch/verify standalone; prepared artifacts MUST need only Python at runtime.
- **FR-011**: Initial/manual catalog sync MUST work without availability selections, coalesce active refresh requests, and report progress/per-provider failures.
- **FR-012**: Startup MUST reject unsupported database/worker settings and missing/unwritable resources with corrective messages.
- **FR-013**: Background calls/parsing and database contention MUST NOT prevent unrelated HTTP responses.
- **FR-014**: Static serving/history MUST protect credentials and files outside frontend assets, retaining existing security boundaries.
- **FR-015**: Automated behavior, migration, restart, minimal-install, browser, and distributed regression checks MUST verify the feature.

### Key Entities

- **Runtime capabilities**: Execution mode, monitoring support, scheduler health, and last discovery.
- **Shared target/subscription**: Existing de-duplicated provider/date request and individually filtered user interest.
- **Pending notification**: Detection event, subscription, credential-free alert content, retry timing/count, and terminal delivery/skip result.
- **Job attempt**: Bounded recent job/event identity, provider/target context, timing, and outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A prepared installation completes initial sync → search → create → detect → notify with one website/API origin and zero backing services or excluded libraries.
- **SC-002**: Fresh/populated upgrades and restart/backup/restore preserve all seeded state and resume pending alerts.
- **SC-003**: Two eligible subscribers produce one provider check per due cycle and alerts only for currently matching subscriptions.
- **SC-004**: In a deterministic small-install test with successful external responses and no backlog, delivery begins within 60 seconds of detection; unrelated health responds within 2 seconds while provider/catalog work is held pending.
- **SC-005**: Fault tests cover failure before/after persistence, restart, retry exhaustion, and changed eligibility; no committed pending alert is silently lost and failed checks preserve results.
- **SC-006**: Local admin explains limits and reports injected runner failure as unhealthy; distributed regression/live monitoring smoke checks pass.
- **SC-007**: An installed artifact works outside the checkout without build tools, including deep links, login, and mutations; missing paths and traversal have correct errors.
- **SC-008**: Formatting, lint, types, tests, API contracts, and applicable pre-commit/browser checks pass before implementation is complete.

## Assumptions

- Personal/small shared deployments use local disk and one Python process per database. Multiple replicas, network filesystems, and cross-database conversion are out of scope.
- Node/pnpm build TypeScript before deployment; browsers run compiled JavaScript. Existing separate hosting remains supported.
- Existing `none`, `session`, and `auth0` modes remain independent. Providers, alerts, and optional Auth0 need internet access.
- Historical Prometheus charts are omitted locally; a replacement time-series system, generic durable queue, and new alert channels are out of scope.
- Local attempt history retains at most 1,000 records for 24 hours and clears on restart. Terminal notification records retain 24 hours; pending retries survive.
- Tests use synthetic providers/transports and no live credentials.

## Clarifications

### Session 2026-10-13

No critical ambiguity requires a new question. Scope follows the earlier draft and the request to stop before implementation. Build-time tools, process limits, monitoring omissions, and delivery guarantees are explicit assumptions; storage/interface mechanics are resolved in design. No user answer or approval is invented.
