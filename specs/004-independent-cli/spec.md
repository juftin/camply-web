# Feature Specification: Independent CLI on the Modern Engine

**Created**: 2026-10-12
**Status**: Draft; product direction established, implementation proposed
**Input**: Rebuild the CLI as an independently published member of the larger uv workspace, using standalone provider searches and retiring legacy code in favor of the modern backend engine.
**Design**: [DESIGN_CLI.md](../../docs/agents/DESIGN_CLI.md)

## User stories and acceptance scenarios

### US1: Search without deploying the web application (P1)

A camper installs `camply` and searches a campground/date window with the same provider and matching logic used by the modern backend.

**Independent test:** Install built CLI/core artifacts in an environment without backend services, then run a complete search against a mocked booking API.

1. Given a clean environment, installing the CLI produces working `camply` and `python -m camply` entry points without requiring a repository checkout.
2. Given a valid campground and arrival/checkout window, a search returns current qualifying stays, site identity, and a booking link.
3. Given type/electric/minimum-stay requirements, CLI and backend use shared matching functions and agree on whether a site satisfies those criteria.
4. Given a successful check with no availability, the command reports zero matches and exits successfully.
5. Given invalid dates, an unsupported provider, or a failed provider response, the command reports the corresponding usage/operational error rather than a successful empty search.

### US2: Monitor openings and receive alerts locally (P1)

A camper leaves one CLI process running to check a campground periodically and optionally send Pushover alerts.

**Independent test:** Advance a fake clock through controlled availability and delivery outcomes without live provider requests or notification sends.

1. Given watch mode, the first check occurs immediately and later checks respect the configured interval and provider recovery delays.
2. Given identical consecutive results, repeated alerts are suppressed within the invocation.
3. Given a failed check, the previous successful snapshot is retained; failure is not treated as disappearance.
4. Given disappearance in a successful check followed by reappearance, the opening generates a new alert.
5. Given requested Pushover delivery, credentials are validated before the first provider check and the message describes an actual qualifying stay.
6. Given delivery failure after bounded retries, results remain available and watch mode reports the failure; there is no implied durable delivery guarantee.
7. Given interruption or expiry, clients close and the process finishes according to the documented exit contract.

### US3: Discover campground identifiers locally (P2)

A camper searches provider metadata to find an ID for a subsequent standalone availability check.

**Independent test:** Build a local catalogue from a synthetic RIDB archive, exercise cache freshness/failure behavior, and search it without PostgreSQL.

1. Given no cache, discovery downloads and validates metadata and produces a local catalogue.
2. Given a usable fresh catalogue, discovery reuses it without redownloading.
3. Given refresh failure and a usable stale catalogue, discovery warns and returns metadata results.
4. Given refresh failure and no usable catalogue, discovery reports an operational error.
5. Given a known campground ID, availability checks work without requiring the local discovery catalogue.

### US4: Maintain and release CLI independently (P1)

A maintainer changes shared provider logic once, verifies both consumers, and publishes CLI/core packages independently of application deployment.

Backend and CLI development share one unified uv workspace, lockfile, and environment while distribution versions/releases remain separate.

**Independent test:** Run backend/CLI regressions and install candidate wheels and source-distribution-built wheels outside the checkout.

1. Given a core provider change, both backend and CLI tests run against the shared implementation.
2. Given a CLI release tag, its workflow validates, builds, tests, and publishes only its component's verified artifacts.
3. Given an unpublished required core version, CLI publication cannot complete until that core artifact is resolvable.
4. Given backend-only application changes, no CLI package release occurs automatically.
5. Given stable cutover, the published CLI contains no legacy engine or silent fallback, and removed features have documented migration guidance.
6. Given shared workspace metadata or lock changes, affected Python consumers are checked together; package selection and versions refer to the intended member.

## Functional requirements

- **FR-001:** CLI installation and execution must be independent of a running camply server, database, broker, and repository checkout.
- **FR-002:** Publish the CLI under the existing `camply` identity, with package metadata/versioning in `backend/packages/cli` and an independent release workflow, within the unified uv workspace.
- **FR-003:** Extract reusable modern engine code into a separately published core library under `backend/packages/core`; backend and CLI must consume that implementation.
- **FR-004:** Core must not import application/ORM/broker/terminal modules or initialize credentials/network/telemetry on import.
- **FR-005:** Initially support Recreation.gov, one campground and date window per invocation, minimum stay/type/electric criteria, and qualifying-stay output.
- **FR-006:** Define arrival-inclusive, checkout-exclusive nights; deduplicate dates and reject unknown in-window availability statuses as incomplete/invalid checks.
- **FR-007:** Support one-shot and watch operation with explicit polling units, provider policy, failure handling, cancellation, and exit codes.
- **FR-008:** Separate successful availability state from notification outcome; deliver Pushover through shared transport with explicit credentials.
- **FR-009:** Provide local metadata discovery without reusing PostgreSQL query logic or assuming cached metadata proves current availability.
- **FR-010:** Preserve backend database IDs, API field names, queued notification payload shape, and worker eligibility/transaction responsibilities during extraction.
- **FR-011:** Use uv and Task for development, checks, builds, and artifact verification; resolve CLI alongside core, db, and workers in the uv workspace while keeping published runtime dependencies explicit and service-free CLI checks available.
- **FR-012:** Verify wheels and source-distribution-built wheels in clean environments without editable imports or local runtime paths.
- **FR-013:** Retire legacy source after replacement acceptance; full legacy feature parity is not required and unsupported capabilities must fail explicitly.
- **FR-014:** Document support/version/licensing decisions before publication; preserve existing applicable notices and old release pinning guidance.
- **FR-015:** Nest CLI inside `backend/packages/cli` alongside core, db, providers, and worker, maintaining container isolation so CLI is never installed in backend images.

## Edge cases

- Checkout at a month/year boundary; leap day; duplicated, unordered, or gapped available dates.
- A requested minimum stay longer than the window or a monitored window that expires while running.
- Provider rate limiting, open circuit breaker, unknown status, invalid payload, and incomplete check.
- Missing campsite metadata or catalogue names with valid live availability.
- Cache corruption, interrupted download, missing Content-Length, stale catalogue, and concurrent writers.
- Notification timeout after a possibly successful send; restart of session-only monitoring state.
- Legacy flags whose units changed, unsupported legacy provider names, and unknown configuration keys.
- Sequential backend tasks using separate event loops and already queued notification messages.
- Development checkout imports hiding missing packages or pulling in legacy source.
- Shared dependency conflicts, concurrent subset synchronization of the root environment, and old Task/container paths selecting the wrong project.

## Key entities

- **Provider descriptor:** Stable provider identity, display name, and request/booking policies without database state.
- **Search target/window:** Provider-scoped campground ID and arrival/checkout dates.
- **Search filters:** Minimum consecutive nights, preferred campsite types, and electric requirement.
- **Campsite/stay:** Provider-normalized site details and qualifying consecutive night runs.
- **Availability snapshot:** A complete successful set of site/night observations for comparison.
- **Metadata catalogue:** Cache-versioned discovery records with fetch time, independent of live inventory.
- **Notification payload/credentials:** Existing-compatible alert data plus explicit runtime credentials.

## Success criteria

- **SC-001:** Built CLI/core artifacts perform a mocked end-to-end search in a clean environment with backend service distributions absent.
- **SC-002:** Both applications use the same provider client, matching primitives, comparison function, and Pushover transport; no replacement functionality imports legacy code.
- **SC-003:** Existing backend tests and new contract/regression tests pass after extraction, including dates/statuses and queued payload compatibility.
- **SC-004:** Watch tests prove unchanged-result suppression, failure snapshot preservation, reappearance detection, bounded delivery failure, and cleanup.
- **SC-005:** Local discovery tests pass without PostgreSQL and preserve usable cache data after failed refresh.
- **SC-006:** Independent release gates validate installed wheels/source distributions and component-specific versions/tags before publishing.
- **SC-007:** Stable cutover removes the legacy runtime and its obsolete tooling while documenting the supported surface and intentional breaks.
- **SC-008:** The unified workspace lock covers CLI alongside core, db, and workers; member checks pass, and clean artifact tests prove standalone publication.

## Exclusions

Full legacy provider/channel parity, account/server management, durable local scans or delivery queues, cross-process deduplication, additional advanced filters, multiple targets, legacy YAML migration, TUI, and CLI Docker publication are outside this feature.
