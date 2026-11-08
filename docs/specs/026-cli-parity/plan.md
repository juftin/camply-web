# CLI parity: design outline

**Status**: Proposed; no runtime implementation. See [specification](spec.md), [source audit](legacy-audit.md) and [tasks](tasks.md).

## Existing logic audit

- `src/camply/cli/main.py` is a Click group with help/version, standalone and role serving, health checks, and lazy `db` resolution. Extend this group; do not replace its current commands.
- `src/camply/providers/base.py` exposes validated async `search`/`search_upstream`, `find_availabilities` and metadata ingestion. Feature [025](../025-provider-search/spec.md) provides database-independent discovery across 13 registered providers. It does not provide a complete public site/equipment/exact-ID resolution contract.
- `src/camply/providers/dto.py` supplies typed discovery results and nightly site availability. Provider-native opaque string identities are already supported. Ticket/time-slot inventory and explicit equipment lengths need richer contracts.
- `src/camply/db/availability.py` implements shared web matching. `src/camply/worker/engine/scanner.py` wraps availability checks in persistent `UniqueTarget`, campground, subscriber eligibility, snapshot replacement and fan-out behavior. A local CLI search cannot call `check_target` without inventing database users/scans.
- `src/camply/worker/notifications` currently contains base/Pushover delivery, and the standalone outbox provides durable retry semantics. Initial CLI delivery is console-only, so no notification extraction/adapter/credential resolver is needed. Keep existing web Pushover delivery unchanged; console results use direct provider links.
- `pyproject.toml` declares `cli | server | worker` as peer layers above providers/db. CLI cannot import worker engine or notification modules directly. Optional-free import contracts cover CLI/providers/db; adding imports is not sufficient to make shared worker code usable there.

## Initial design outline

Scope follows the [specification's D01–D13 registry](spec.md#initial-scope-and-deferred-work). Historical replacement ideas in the audit are future options, not initial design obligations.

1. Extend the current lazy Click group with provider listing, recreation-area/campground discovery and campground-based availability. Use existing Click/plain output; Rich-click, TUI and `configure` are TODOs. Implement the specification's exact option/default/precedence contract and stdout/stderr behavior. Normalize CLI flags only; no YAML loader or legacy `.camply` migration. Provider resolution must distinguish explicit Click parameters from environment/default values so a command-level environment fallback cannot override an explicit root selection.
2. Reuse feature 025's public provider search and current availability methods. Add database-independent exact campground metadata lookup and complete area/campground enumeration. Feature 025 has neither a campground-ID argument nor a public pagination cursor: do not pretend its limited `search` method supplies these contracts. Implement the smallest public provider capabilities required to resolve explicit IDs and enumerate all children, reusing native catalog/request logic. Keep the 50-result display limit, truncation detection and exhaustive availability expansion separate. Test exact IDs outside the displayed page and synthetic areas larger than the 1000-result validation cap. Do not introduce public site catalogs, site-ID resolution or equipment capabilities for deferred workflows.
3. Extract shared matching/stay construction only where needed by initial CLI/web reuse. External CLI notifications, including Pushover, are deferred; do not extract notification interfaces/adapters for this initial scope. A base-only `camply.core` layer is a proposed home, with dependency order `cli | server | worker` → `core` → `providers` → `db` → `__about__`. Confirm the smallest useful extraction before creating it. Update exhaustive Import Linter contracts and architecture documentation together; no upward imports or blanket exceptions.
4. Keep persistent `check_target`, web subscriber eligibility, locks, outbox and alert policy in their current adapters. Local checks should not fabricate users or require database migration/catalog ingestion. Use existing provider-native strings and complete area/campground targets, without accepting individual site selectors.
5. Design and test an internal availability-check operation with bounded async requests, provider pacing/retries, deduplicated targets, typed matching and owned-client cleanup. The public command performs the first check immediately and continues after matching/empty checks until cancelled, without legacy mode switches. A single internal check is a building block, not a public one-pass mode.
6. Render results and provider booking links to the console only. Do not import/dispatch Pushover delivery, query database users, read notification credentials, create `PUSHOVER_USER_KEY`, or add notification options/commands. Existing web notification modules/settings remain unchanged. CLI activation and credentials are future D03 design, along with all external channels, caps and history.
7. **D11 remains open**: intended default is search forever. Brainstorm command lifecycle, the need/meaning of the three old run-mode flags, pacing, stopping, expiry, cancellation outcomes and cron later. The initial default is immediate, continued checking until cancellation, including after a match; test that behavior through the public command. Detailed scheduling/failure/expiry/alert policy and the legacy flag matrix remain deferred. Do not carry forward the old flag-only one-pass default or implicit-continuous triggers as requirements.

## Deferred design references

Keep the [source audit](legacy-audit.md) and [TODO backlog](tasks.md#deferred-todo-registry) for later work. No initial shared schema, provider adapter or persistence layer is required solely for these items:

- D01/D02: site catalogs, individual campsite selection and site-to-parent lookup.
- D03: all external CLI delivery including Pushover, activation/credentials, full channel parity and test-notifications.
- D04: missing campground providers/catalogs, Yellowstone and all legacy GoingToCamp deployments/facade.
- D05/D10: YAML compatibility, legacy `.camply` migration and configuration wizard.
- D06/D07: permits, tickets/tours/timed entry, slots/quantities and equipment catalogs/filtering.
- D08/D09: TUI and Rich-click.
- D12/D13: first-batch notification controls, persistent JSON history, offline flags and state migration.

Legacy deployment IDs, notification caps and YAML precedence remain documented facts. They are not promised future designs until their TODOs are revisited. General permit support is a requested future feature; the audited ticket/tour providers are not evidence of broader legacy permit support.

## Constitution review

Use Python >=3.11, development/default CI 3.14, Pydantic v2 and async IO. Preserve one distribution and optional dependency independence. Any core extraction requires an intentional architecture/governance/import-contract review and negative boundary tests. Live observations remain the only availability authority. This scope requires no CLI history file, application database, frontend change or new inventory schema.

## Delivery and validation

Initial order: scope/capability fixtures → current-provider discovery and internal availability checks → availability command with search-forever as the default direction and console-only output → initial release gates. D11 is a later brainstorming item for detailed modes/flags. Deferred TODOs are not initial release gates or follow-on implementation authorization.

Use Click runner tests for every public option, precedence and validation rule, synthetic HTTP contracts for current providers, matching/stay fixtures and installed wheel/sdist checks on Python 3.11/3.14. Verify current provider aliases/identities and unsupported inputs without requiring all historical deployment/channel mappings to execute. Protect existing serve/db/standalone/distributed behavior and optional-free imports. The minimum public-command monitoring/cleanup tests below are initial acceptance gates; only additional D11 policies wait for later design. YAML/state/permit/equipment/TUI/new-channel tests wait for their TODOs.

Implementation gates: `task test`, `task check`, `task lint`, appropriate installed-artifact tasks and `task docs:check`. For this documentation change, verify formatting, site rendering/links and consistency between initial requirements and the TODO registry.

## Public command acceptance strategy

1. Parameterized Click runner tests exercise actual command dispatch and normalization: canonical provider names/aliases, command/root/environment/default conflicts, explicit no-debug, repeated selectors/date pairs/weekdays, unknown IDs and deferred options. Assert provider request arguments and output streams; do not call only the normalized-request constructor.
2. In isolated base wheel and sdist-rebuilt-wheel environments, run the installed `camply` executable from a temporary directory outside the checkout. Use synthetic local upstream HTTP responses through provider client/endpoint test seams; do not import repository source or replace the command callback/runner. The HTTP transcript must prove supplied IDs/windows reached the provider. No live booking service or real notification credentials are needed.
3. Script a first matching response and a subsequent successful response. Verify printed stays, a second completed request cycle and that the process has not exited after the match. Use an injected clock/wait seam for deterministic in-process tests and a bounded test cadence for the subprocess fixture; no user-facing test-only cadence flag is needed. Tests must not wait for a production polling interval.
4. Send Ctrl-C/SIGTERM in subprocess tests and assert termination with no orphan polling. Separately instrument in-process client/task ownership and assert closure/cancellation and no scheduled requests after stop. A kill/timeout is test cleanup, not evidence the application shut down correctly. Do not prescribe deferred signal exit codes or detailed expiry behavior through these tests.
5. Assert console results with notification settings absent/malformed and zero external-notification requests, database-user reads or delivery dispatch. `--notifications pushover` and `test-notifications` must fail as deferred inputs; existing web notification regressions remain green.
6. Invalid dates/constraints, conflicting selectors under the documented precedence, missing required inputs and unsupported/deferred switches must be observed at the public parser/resolution boundary. Failures cannot be hidden by internal-operation tests passing.
