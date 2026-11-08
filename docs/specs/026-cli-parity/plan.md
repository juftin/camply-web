# CLI parity: design outline

**Status**: Proposed; no runtime implementation. See [specification](spec.md), [source audit](legacy-audit.md) and [tasks](tasks.md).

## Existing logic audit

- `src/camply/cli/main.py` is a Click group with help/version, standalone and role serving, health checks, and lazy `db` resolution. Extend this group; do not replace its current commands.
- `src/camply/providers/base.py` exposes validated async `search`/`search_upstream`, `find_availabilities` and metadata ingestion. Feature [025](../025-provider-search/spec.md) provides database-independent discovery across 13 registered providers. It does not provide a complete public site/equipment/exact-ID resolution contract.
- `src/camply/providers/dto.py` supplies typed discovery results and nightly site availability. Provider-native opaque string identities are already supported. Ticket/time-slot inventory and explicit equipment lengths need richer contracts.
- `src/camply/db/availability.py` implements shared web matching. `src/camply/worker/engine/scanner.py` wraps availability checks in persistent `UniqueTarget`, campground, subscriber eligibility, snapshot replacement and fan-out behavior. A local CLI search cannot call `check_target` without inventing database users/scans.
- `src/camply/worker/notifications` currently contains base/Pushover delivery, and the standalone outbox provides durable retry semantics. Other legacy channels are gaps. CLI needs direct booking links, not the default web summary link.
- `pyproject.toml` declares `cli | server | worker` as peer layers above providers/db. CLI cannot import worker engine or notification modules directly. Optional-free import contracts cover CLI/providers/db; adding imports is not sufficient to make shared worker code usable there.

## Proposed design

1. Add lazy Click commands and a typed compatibility normalization layer under `camply.cli`. Parse flags/YAML once into a request, then perform capability/configuration preflight. Render output separately from provider execution.
2. Add explicit public provider capabilities for target resolution, complete area enumeration, site catalogs, equipment catalogs and scan restrictions. Reuse existing catalog/client logic. Unsupported optional methods return a typed capability error, not an empty list. Separate interactive discovery limits from exhaustive target expansion.
3. Extract reusable matching/stay construction, foreground orchestration primitives and notification interfaces/adapters into a base-only `camply.core` layer. Keep provider IO in providers and database operations in persistence/adapters. Proposed dependency order: `cli | server | worker` → `core` → `providers` → `db` → `__about__`. Both top-level adapters and core may use lower layers; no upward imports. Update exhaustive Import Linter contracts and documented boundaries in the same implementation change. Confirm extracted modules import no optional runtime dependencies.
4. Keep worker `check_target`, subscription eligibility, locks, web outbox and web alert policy as adapters. Reuse pure night/filter logic from core, with CLI exact-length stay rendering and lifetime seen suppression explicitly selected by policy. Do not fabricate users or require Alembic for state-free CLI searches.
5. The foreground runner checks immediately, deduplicates provider-qualified targets/windows and uses bounded async concurrency. Apply shared client retries and provider pacing plus CLI intervals. Await completion/delivery/state flush for one-cycle modes, and use cancellable waits and owned client shutdown for monitoring.
6. Store optional CLI history independently as versioned JSON with atomic replacement and a single-writer guard. Import legacy arrays through a validated compatibility model with explicit provider context; track successful per-channel delivery separately from observation. Cap suppression records deliberately and visibly if a retention policy is introduced; do not silently expire lifetime suppression. External acceptance/crash duplicates remain possible.
7. Put modern and legacy notification settings through one typed resolver. Map legacy Pushover keys explicitly; if both old/new app-token variables are set inconsistently, fail with a redacted conflict error. An app token must be supplied when no distributable supported default exists; explain the setup change. Keep SMTP/SDK/Apprise/TUI dependencies optional and lazy. Choose direct adapters versus Apprise only after payload/recipient/failure equivalence tests; generic webhook requires its own legacy serializer.
8. Resolve `GoingToCamp` through a deployment compatibility facade, not a single native-provider alias. A deployment selector chooses a provider/catalog; native parks are then resolved from that deployment. Preserve a stable mapping for all 17 old selectors even while implementations are unavailable. Validate IDs against current catalogs before accepting migration claims.
9. Add dedicated typed inventory for tickets/slots/quantity and Yellowstone facility availability after upstream verification. Update provider/data architecture designs and any persistence contracts only if those inventories also enter web scheduling; CLI parity alone does not require changing web schema or APIs.

## Constitution review

Use Python >=3.11, development/default CI 3.14, Pydantic v2 and async IO. Preserve one distribution and optional dependency independence. The new core layer requires an intentional governance/documentation and Import Linter update, with negative import-boundary tests; no blanket ignored imports. Live observations remain the only availability authority; JSON history only suppresses repeats. No database migration is required by this documentation change; future model changes require migrations. No frontend change is required.

## Delivery and validation

Delivery order is [tasks](tasks.md): shared contracts/foundations → discover and one-pass → monitoring/YAML/history/Pushover → all channels/TUI → missing inventories/deployments and full parity claim. Each slice ships its coverage matrix and honest gaps; task order does not promise unavailable upstream APIs can be restored immediately.

Use Click runner contracts, frozen-clock runner tests, synthetic HTTP provider tests and sanitized baseline YAML/JSON fixtures. Verify every 19-name/17-deployment mapping rather than assuming an API family covers every destination. Record new live provider evidence separately without credentials; do not reuse years-old VCR dates as evidence of current endpoint health. Test wheel and sdist-rebuilt wheel outside the checkout on Python 3.11/3.14 with base and optional extras, plus existing serve/db/standalone/distributed regressions.

Implementation gates: `task test`, `task check`, `task lint`, appropriate installed-artifact tasks and `task docs:check`; no new ad hoc development command required. Documentation-only review checks include Markdown/link integrity and consistency of the inventory, requirements and task coverage.
