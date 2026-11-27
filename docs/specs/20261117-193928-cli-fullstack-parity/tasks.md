---
description: "Task list for CLI Full-Stack Parity (20261117-193928-cli-fullstack-parity)"
---

# Tasks: CLI Full-Stack Parity

**Input**: Design documents from `/docs/specs/20261117-193928-cli-fullstack-parity/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required for user stories), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli-contract.md](contracts/cli-contract.md), [quickstart.md](quickstart.md)

**Tests**: Included in accordance with Constitution Principle V (Automated Verification & Test-First Mentality) and [quickstart.md](quickstart.md).

**Organization**: Tasks are grouped by user story (`US1`–`US4`) to enable independent implementation and testing of each increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Exact repository file paths and verbatim `data-model.md` constraints are included in every task description.

## Path Conventions

- **Application**: `src/camply/cli/`, `src/camply/core/`, `docs/`, and `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify baseline CLI/core test suite and Import Linter boundaries before introducing new CLI options and modules.

- [x] T001 Verify baseline CLI, core search, and Import Linter checks pass for `src/camply/cli/`, `src/camply/core/search.py`, and `pyproject.toml` (`uv run pytest tests/cli/ tests/core/ && uv run lint-imports`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared reusable Click option factories and logging stream helpers in `src/camply/cli/` that multiple user stories depend on.

**⚠️ CRITICAL**: Complete this phase before beginning user story implementation.

- [x] T002 Add reusable Click option decorators to `src/camply/cli/options.py` for `--campsite` (repeatable string), `--campsite-type` (repeatable case-insensitive `TENT`, `RV`, `CABIN`, `OTHER`), `--electric` (`is_flag=True`, default `False`), `--accessible` (`is_flag=True`, default `False`), `--rv-length` (`type=click.IntRange(min=1, max=200)`, default `None`), `--notifications` (repeatable case-insensitive `pushover`, `ntfy`), `--state-file` (`type=click.Path(dir_okay=False, path_type=Path)`, default `None`), `--search-once` (`is_flag=True`, default `False`), `--interval` (`type=click.IntRange(min=5)`, default `10` minutes), `--limit` (`type=click.IntRange(min=1, max=500)`, default `50`), and `--json` (`is_flag=True`, default `False`)
- [x] T003 [P] Update `set_up_logging` and `diagnostic` in `src/camply/cli/output.py` to accept `stderr_only: bool = False` so that when `--json` is active, all log levels (including `INFO` and `CAMPLY_LOG_LEVEL`) route exclusively to `sys.stderr` while keeping `sys.stdout` clean for structured JSON payloads

**Checkpoint**: Shared CLI option decorators and stderr-isolated logging are ready — user stories can now proceed.

---

## Phase 3: User Story 1 - Filter terminal availability searches by site type, equipment, hookups, accessibility, and specific sites (Priority: P1) 🎯 MVP

**Goal**: Allow `camply campsites` users to filter availability by campsite types (`TENT`, `RV`, `CABIN`, `OTHER`), electric hookup (`--electric`), ADA accessibility (`--accessible`), minimum RV/trailer length (`--rv-length` in feet `1..200`), and parent-scoped `--campsite` IDs/names; validate filters upfront against `ProviderFilterCapabilities`; and display supported site filters in `camply providers`.

**Independent Test**: Run `uv run pytest tests/core/test_search.py tests/cli/test_search.py` to verify `SearchRequest` and `camply campsites` include only sites matching all active filters, fail closed on unknown attributes (`max_vehicle_length is None` or `is_accessible is False`), reject unsupported provider filters or `--campsite` without `--campground`/`--rec-area` before making HTTP requests, and list provider filter capabilities in `camply providers`.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation.**

- [x] T004 [P] [US1] Add unit tests in `tests/core/test_search.py` for `SearchRequest` and `site_matches_request` covering `campsites: tuple[str, ...] = ()` (exact ID and case-insensitive name matching), `campsite_types: tuple[CampsiteType, ...] = ()` (`TENT`, `RV`, `CABIN`, `OTHER`), `require_electric: bool = False` (`is_electric is True`), `require_accessible: bool = False` (`is_accessible is True`), and `min_rv_length: int | None = None` (`ge=1, le=200`, failing closed when `max_vehicle_length is None` or `< min_rv_length`)
- [x] T005 [P] [US1] Add Click runner tests in `tests/cli/test_search.py` for `camply campsites` (`--campsite`, `--campsite-type`, `--electric`, `--accessible`, `--rv-length`), verifying upfront rejection when `--campsite` is passed without `--campground` or `--rec-area`, rejection of blank `--campsite` selectors, rejection of out-of-range `--rv-length` (`<= 0` or `> 200`), rejection of filters unsupported by a provider's `filter_capabilities`, and filter capability output in `camply providers`

### Implementation for User Story 1

- [x] T006 [US1] Extend `SearchRequest`, `normalize_request`, and `_stays` in `src/camply/core/search.py` with `campsites: tuple[str, ...] = ()`, `campsite_types: tuple[CampsiteType, ...] = ()`, `require_electric: bool = False`, `require_accessible: bool = False`, and `min_rv_length: int | None = Field(default=None, ge=1, le=200)`, implementing `site_matches_request(site: CampsiteDTO, request: SearchRequest) -> bool` with fail-closed semantics matching `camply.db.availability.matches_scan_filters`
- [x] T007 [US1] Update `render_providers` in `src/camply/cli/output.py` to format and log each provider's `filter_capabilities` (`preferred_types`, `require_electric`, `require_accessible`, `min_rv_length`) from `provider_class.filter_capabilities`
- [x] T008 [US1] Update `campsites_cmd` in `src/camply/cli/campsites.py` to wire `--campsite`, `--campsite-type`, `--electric`, `--accessible`, and `--rv-length`, validate that `--campsite` is accompanied by at least one `--campground` or `--rec-area`, validate active filters against `provider_class.filter_capabilities` before resolving targets or issuing HTTP requests, and pass normalized filters into `normalize_request`

**Checkpoint**: User Story 1 (`US1`) is complete and independently testable (`uv run pytest tests/core/test_search.py tests/cli/test_search.py`).

---

## Phase 4: User Story 2 - Receive Pushover and ntfy alerts with duplicate suppression from the CLI (Priority: P1)

**Goal**: Deliver availability alerts from `camply campsites` via Pushover and ntfy using `--notifications` (`pushover`, `ntfy`) and environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`); provide `camply test-notifications`; and suppress duplicate alerts across continuous cycles and optional `--state-file` single-pass runs.

**Independent Test**: Run `uv run pytest tests/cli/test_notifications.py` to verify `camply test-notifications` and `camply campsites --notifications` validate credentials, send alerts on newly opened and reopened stays, suppress unchanged stays across cycles and `--state-file` runs, preserve state on provider poll errors, and redact secrets in logs/errors.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation.**

- [x] T009 [P] [US2] Create unit and Click runner tests in `tests/cli/test_notifications.py` covering `CLINotificationConfig` validation (`channels: tuple[Literal["pushover", "ntfy"], ...] = ()`, `PUSHOVER_USER_KEY` / `PUSHOVER_APP_TOKEN` required for `pushover`, `ntfy_topic` matching `^[A-Za-z0-9_-]{1,64}$` required for `ntfy`, `ntfy_server_url` validated via `validate_ntfy_url` defaulting to `"https://ntfy.sh"`, printable ASCII `NTFY_ACCESS_TOKEN`), `camply test-notifications` success/failure exit codes, `StayDeduplicationState` in-memory and `--state-file` JSON persistence across cycles/reopens/provider-errors, zero credential reads when `--notifications` is omitted, and secret redaction on failures

### Implementation for User Story 2

- [x] T010 [US2] Create `src/camply/cli/notifications.py` implementing `CLINotificationConfig` (with `repr=False` on `pushover_user_key`, `pushover_app_token`, and `ntfy_access_token`), `StayDeduplicationState` (canonical stay key `"{provider_id}:{campground_id}:{campsite_id}:{arrival.isoformat()}:{checkout.isoformat()}"` and atomic `--state-file` JSON v1 read/write), `send_stay_notifications` (dispatching `NotificationDTO` via `PushoverProvider.send_accepted` and `NtfyProvider.send_accepted` with sanitized error logging), and `test_notifications_cmd`
- [x] T011 [US2] Register `test-notifications` lazily in `CamplyCLI.list_commands` and `CamplyCLI.get_command` in `src/camply/cli/main.py`
- [x] T012 [US2] Wire `--notifications` and `--state-file` into `campsites_cmd` in `src/camply/cli/campsites.py`, validating `CLINotificationConfig` and initializing `StayDeduplicationState` before starting availability checks and dispatching alerts only for newly opened or reopened stays after each successful check cycle

**Checkpoint**: User Stories 1 AND 2 are both complete and independently testable (`uv run pytest tests/cli/test_notifications.py tests/cli/test_search.py`).

---

## Phase 5: User Story 3 - Browse beyond 50 live discovery results and use canonical provider names across CLI commands (Priority: P2)

**Goal**: Support `--limit` (`1..500`, default `50`) on live database-free `camply recreation-areas` and `camply campgrounds` discovery while preserving truncation warnings (`limit + 1` upstream probe), and allow `camply db metadata` to accept canonical provider names/aliases in addition to numeric IDs and `all`.

**Independent Test**: Run `uv run pytest tests/cli/test_search.py tests/cli/test_main.py` to verify `--limit` controls displayed discovery results and truncation warnings without database access, and `camply db metadata` resolves canonical provider names (e.g., `RecreationDotGov`, `ReserveCalifornia`) case-insensitively.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation.**

- [x] T013 [P] [US3] Add Click runner tests in `tests/cli/test_search.py` for `--limit` (`1..500`, default `50`) on `camply recreation-areas` and `camply campgrounds`, verifying custom result caps, `limit + 1` upstream truncation probing, dynamic truncation warning messages, and rejection of out-of-range `--limit` values (`0`, `501`)
- [x] T014 [P] [US3] Add Click runner tests in `tests/cli/test_main.py` for `camply db metadata` verifying case-insensitive canonical provider names (e.g. `--provider-id RecreationDotGov`, `--provider ReserveCalifornia`), provider class aliases (`RecreationGovProvider`), numeric IDs (`1`), `all`, and actionable errors on unknown provider names

### Implementation for User Story 3

- [x] T015 [US3] Update `discovery_query` in `src/camply/cli/discovery.py` and `render_discovery` in `src/camply/cli/output.py` to accept `limit: int = DISPLAY_LIMIT`, request `limit + 1` as the upstream probe in `ProviderSearchQuery`, slice displayed results to ` ordered[:limit]`, and report `"Showing %s results; more results exist. Narrow --search or --state."` when `len(ordered) > limit`
- [x] T016 [US3] Wire `@options.limit()` into `recreation_areas_cmd` in `src/camply/cli/recreation_areas.py` and `campgrounds_cmd` in `src/camply/cli/campgrounds.py`, passing `limit` through `discovery_query`, `instance.search`, and `render_discovery`
- [x] T017 [US3] Update `metadata_cmd` in `src/camply/cli/db.py` to accept canonical provider names and class-name aliases (via `provider_entries()` from `camply.cli.providers`) as well as numeric provider IDs (`1`–`26`) and `all` on `--provider-id` and `--provider`

**Checkpoint**: User Story 3 (`US3`) is complete and independently testable (`uv run pytest tests/cli/test_search.py tests/cli/test_main.py`).

---

## Phase 6: User Story 4 - Control run cadence and emit JSON output (Priority: P2)

**Goal**: Support single-pass execution (`--search-once`) and custom polling intervals (`--interval` `>= 5` minutes) on `camply campsites`, and support machine-readable `--json` stdout output on `providers`, `recreation-areas`, `campgrounds`, and `campsites --search-once` with all logs routed to `stderr`.

**Independent Test**: Run `uv run pytest tests/core/test_search.py tests/cli/test_search.py` to verify `camply campsites --search-once` exits `0` after one check cycle, `--interval` enforces `>= 5` minutes and passes the converted delay in seconds to `monitor()`, and `--json` outputs valid JSON arrays on `stdout` for `providers`, `recreation-areas`, `campgrounds`, and `campsites --search-once` while rejecting `campsites --json` without `--search-once`.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation.**

- [x] T018 [P] [US4] Add unit and Click runner tests in `tests/core/test_search.py` and `tests/cli/test_search.py` for `monitor(..., once=True)`, `camply campsites --search-once`, `camply campsites --interval` (valid `>= 5` minutes and rejected `< 5` or non-integer), and `--json` output on `providers`, `recreation-areas`, `campgrounds`, and `campsites --search-once` (including rejection of `campsites --json` without `--search-once` and verification that `stdout` parses as pure JSON with logs on `stderr`)

### Implementation for User Story 4

- [x] T019 [US4] Update `monitor` in `src/camply/core/search.py` to accept `once: bool = False`, returning after the first completed `check_availability` and `on_results` callback when `once=True` without calling `wait(delay)`
- [x] T020 [US4] Add JSON stdout serialization helpers (`render_providers_json`, `render_discovery_json`, `render_stays_json`) in `src/camply/cli/output.py` matching the payload schemas in `docs/specs/20261117-193928-cli-fullstack-parity/data-model.md`
- [x] T021 [US4] Wire `--json` into `providers_cmd` (`src/camply/cli/providers.py`), `recreation_areas_cmd` (`src/camply/cli/recreation_areas.py`), and `campgrounds_cmd` (`src/camply/cli/campgrounds.py`), passing `stderr_only=json_output` to `diagnostic` and emitting JSON to `stdout` when `--json` is set
- [x] T022 [US4] Wire `--search-once`, `--interval`, and `--json` into `campsites_cmd` in `src/camply/cli/campsites.py`, rejecting `--json` when `--search-once` is `False`, passing `stderr_only=json_output` to `diagnostic`, and forwarding `once=search_once` and `interval=interval` to `monitor`

**Checkpoint**: All four user stories (`US1`–`US4`) are complete and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Installed base-wheel packaging verification, user documentation updates, checklist tracking, and full monorepo quality gates.

- [x] T023 [P] Extend installed base-wheel subprocess tests in `tests/packaging/test_cli_search.py` to verify `--campsite-type`, `--electric`, `--accessible`, `--rv-length`, `--campsite`, `--search-once`, `--json`, `--limit`, `camply test-notifications`, and `camply campsites --notifications` (with `--state-file` deduplication) in an isolated wheel environment without `server` or `distributed` extras
- [x] T024 [P] Update user-facing CLI documentation in `docs/cli.md` and feature checklist in `docs/CHECKLIST.md` to document site/equipment filtering, Pushover/ntfy notifications, `--state-file`, `--search-once`, `--interval`, `--limit`, `--json`, and `camply db metadata` provider names
- [x] T025 Run full validation gates from `docs/specs/20261117-193928-cli-fullstack-parity/quickstart.md` (`task fix`, `task lint`, `task check`, `task test`, and `task docs:check`) and confirm zero errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (`T001`) — blocks all user story phases (`T002`–`T003`).
- **User Story 1 (Phase 3 - P1 🎯 MVP)**: Depends on Foundational (`T002`–`T003`).
- **User Story 2 (Phase 4 - P1)**: Depends on Foundational (`T002`–`T003`); integrates into `src/camply/cli/campsites.py` after `T008` (or sequentially in priority order).
- **User Story 3 (Phase 5 - P2)**: Depends on Foundational (`T002`–`T003`); touches `discovery.py`, `recreation_areas.py`, `campgrounds.py`, and `db.py` independently of `US1`/`US2`.
- **User Story 4 (Phase 6 - P2)**: Depends on Foundational (`T002`–`T003`) and builds cleanly on `US1`–`US3` command handlers.
- **Polish (Phase 7)**: Depends on completion of `US1`–`US4`.

### Within Each User Story

1. Write story tests first (`T004`–`T005`, `T009`, `T013`–`T014`, `T018`) and verify they fail before implementation.
2. Implement core/helper modules (`src/camply/core/search.py`, `src/camply/cli/notifications.py`, `src/camply/cli/discovery.py`, `src/camply/cli/output.py`).
3. Wire Click command entrypoints (`src/camply/cli/campsites.py`, `src/camply/cli/main.py`, `src/camply/cli/providers.py`, `src/camply/cli/recreation_areas.py`, `src/camply/cli/campgrounds.py`, `src/camply/cli/db.py`).
4. Verify the story checkpoint passes before advancing.

### Parallel Opportunities

- **Foundational**: `T002` (`src/camply/cli/options.py`) and `T003` (`src/camply/cli/output.py`) can run in parallel.
- **User Story 1 Tests**: `T004` (`tests/core/test_search.py`) and `T005` (`tests/cli/test_search.py`) can run in parallel.
- **Cross-Story Parallelism**: After Phase 2 completes, `US2` (`src/camply/cli/notifications.py` + `tests/cli/test_notifications.py`) and `US3` (`src/camply/cli/discovery.py` + `src/camply/cli/db.py`) can be developed in parallel with `US1` (`src/camply/core/search.py`).
- **User Story 3 Tests**: `T013` (`tests/cli/test_search.py`) and `T014` (`tests/cli/test_main.py`) can run in parallel.
- **Polish**: `T023` (`tests/packaging/test_cli_search.py`) and `T024` (`docs/cli.md` + `docs/CHECKLIST.md`) can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch User Story 1 unit and CLI tests in parallel:
Task: "T004 [P] [US1] Add unit tests in tests/core/test_search.py for SearchRequest and site_matches_request"
Task: "T005 [P] [US1] Add Click runner tests in tests/cli/test_search.py for camply campsites filters and provider capabilities"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`–`T003`)
3. Complete Phase 3: User Story 1 (`T004`–`T008`)
4. **STOP and VALIDATE**: Run `uv run pytest tests/core/test_search.py tests/cli/test_search.py` to validate site/equipment/campsite-ID filtering and provider capability reporting independently.

### Incremental Delivery

1. **Foundation** (`T001`–`T003`) → Shared options and logging ready.
2. **US1 (P1)** (`T004`–`T008`) → Site type, electric, ADA, RV length, and campsite-ID filtering + provider filter capabilities.
3. **US2 (P1)** (`T009`–`T012`) → Stateless Pushover & ntfy notifications, `test-notifications`, and cycle/state-file deduplication.
4. **US3 (P2)** (`T013`–`T017`) → Live discovery `--limit` pagination and canonical provider names in `camply db metadata`.
5. **US4 (P2)** (`T018`–`T022`) → `--search-once`, `--interval`, and `--json` output across CLI commands.
6. **Polish** (`T023`–`T025`) → Base-wheel packaging regressions, documentation updates, and full quality gates.
