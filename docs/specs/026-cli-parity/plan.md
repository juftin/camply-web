# CLI parity: design outline

**Status**: Proposed; no runtime implementation. See [specification](spec.md), [source audit](legacy-audit.md) and [tasks](tasks.md).

## Existing logic audit

- `src/camply/cli/main.py` is a Click group with help/version, standalone and role serving, health checks, and lazy `db` resolution. Extend this group; do not replace its current commands.
- `src/camply/providers/base.py` exposes validated async `search`/`search_upstream`, `find_availabilities` and metadata ingestion. Feature [025](../025-provider-search/spec.md) provides database-independent discovery across 13 registered providers. It does not provide a complete public site/equipment/exact-ID resolution contract.
- `src/camply/providers/dto.py` supplies typed discovery results and nightly site availability. Provider-native opaque string identities are already supported. Ticket/time-slot inventory and explicit equipment lengths need richer contracts.
- `src/camply/db/availability.py` implements shared web matching. `src/camply/worker/engine/scanner.py` wraps availability checks in persistent `UniqueTarget`, campground, subscriber eligibility, snapshot replacement and fan-out behavior. A local CLI search cannot call `check_target` without inventing database users/scans.
- `src/camply/worker/notifications` currently contains base/Pushover delivery, and the standalone outbox provides durable retry semantics. Other legacy channels are gaps. CLI needs direct booking links, not the default web summary link.
- `pyproject.toml` declares `cli | server | worker` as peer layers above providers/db. CLI cannot import worker engine or notification modules directly. Optional-free import contracts cover CLI/providers/db; adding imports is not sufficient to make shared worker code usable there.

## Initial design outline

Scope follows the [specification's D01–D13 registry](spec.md#initial-scope-and-deferred-work). Historical replacement ideas in the audit are future options, not initial design obligations.

1. Extend the current lazy Click group with provider listing, recreation-area/campground discovery and campground-based availability. Use existing Click/plain output; Rich-click, TUI and `configure` are TODOs. Normalize CLI flags only; no YAML loader or legacy `.camply` migration.
2. Reuse feature 025's public provider search and current availability methods. Add only the area/campground target enumeration needed for complete searches. Keep interactive result limits distinct from exhaustive target expansion. Do not introduce public site catalogs, site-ID resolution or equipment capabilities for deferred workflows.
3. Extract shared matching/stay construction and existing notification interfaces only where needed by initial CLI/web reuse. A base-only `camply.core` layer is a proposed home, with dependency order `cli | server | worker` → `core` → `providers` → `db` → `__about__`. Confirm the smallest useful extraction before creating it. Update exhaustive Import Linter contracts and architecture documentation together; no upward imports or blanket exceptions.
4. Keep persistent `check_target`, web subscriber eligibility, locks, outbox and alert policy in their current adapters. Local checks should not fabricate users or require database migration/catalog ingestion. Use existing provider-native strings and complete area/campground targets, without accepting individual site selectors.
5. Design and test an internal availability-check operation with bounded async requests, provider pacing/retries, deduplicated targets, typed matching and owned-client cleanup. A single internal check is a building block, not a decision to expose a one-pass CLI mode.
6. Reuse current Pushover delivery and environment settings where needed, with usable provider booking links and visible failures. Do not add legacy channel adapters, webhook serializers, first-batch caps, configure or per-channel history. Do not promise legacy lifetime duplicate suppression before the monitoring discussion.
7. **D11 remains open**: intended default is search forever. Brainstorm command lifecycle, the need/meaning of the three old run-mode flags, pacing, stopping, expiry, cancellation outcomes and cron later. Use search-forever as the default direction for initial availability; the detailed legacy flag matrix remains deferred. Do not carry forward the old flag-only one-pass default or implicit-continuous triggers as requirements.

## Deferred design references

Keep the [source audit](legacy-audit.md) and [TODO backlog](tasks.md#deferred-todo-registry) for later work. No initial shared schema, provider adapter or persistence layer is required solely for these items:

- D01/D02: site catalogs, individual campsite selection and site-to-parent lookup.
- D03: additional notification providers, full channel parity and multi-channel diagnostics.
- D04: missing campground providers/catalogs, Yellowstone and all legacy GoingToCamp deployments/facade.
- D05/D10: YAML compatibility, legacy `.camply` migration and configuration wizard.
- D06/D07: permits, tickets/tours/timed entry, slots/quantities and equipment catalogs/filtering.
- D08/D09: TUI and Rich-click.
- D12/D13: first-batch notification controls, persistent JSON history, offline flags and state migration.

Legacy deployment IDs, notification caps and YAML precedence remain documented facts. They are not promised future designs until their TODOs are revisited. General permit support is a requested future feature; the audited ticket/tour providers are not evidence of broader legacy permit support.

## Constitution review

Use Python >=3.11, development/default CI 3.14, Pydantic v2 and async IO. Preserve one distribution and optional dependency independence. Any core extraction requires an intentional architecture/governance/import-contract review and negative boundary tests. Live observations remain the only availability authority. This scope requires no CLI history file, application database, frontend change or new inventory schema.

## Delivery and validation

Initial order: scope/capability fixtures → current-provider discovery and internal availability checks → availability command with search-forever as the default direction and any existing Pushover reuse → initial release gates. D11 is a later brainstorming item for detailed modes/flags. Deferred TODOs are not initial release gates or follow-on implementation authorization.

Use Click runner tests for initial commands, synthetic HTTP contracts for current providers, matching/stay fixtures and installed wheel/sdist checks on Python 3.11/3.14. Verify current provider aliases/identities and unsupported inputs without requiring all historical deployment/channel mappings to execute. Protect existing serve/db/standalone/distributed behavior and optional-free imports. Add lifecycle tests once D11 is designed; YAML/state/permit/equipment/TUI/new-channel tests wait for their TODOs.

Implementation gates: `task test`, `task check`, `task lint`, appropriate installed-artifact tasks and `task docs:check`. For this documentation change, verify formatting, site rendering/links and consistency between initial requirements and the TODO registry.
