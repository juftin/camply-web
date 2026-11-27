# Implementation Plan: CLI Full-Stack Parity

**Branch**: `20261117-193928-cli-fullstack-parity` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from [docs/specs/20261117-193928-cli-fullstack-parity/spec.md](spec.md)

## Summary

Bring the stateless `camply` CLI to parity with the full-stack application's filtering, notification, discovery-pagination, and scripting capabilities:

1. Add site-attribute and equipment filtering (`--campsite-type`, `--electric`, `--accessible`, `--rv-length`, and parent-scoped `--campsite`) to `camply campsites` and display `ProviderFilterCapabilities` in `camply providers` (`US1`).
2. Add Pushover and ntfy alerting (`--notifications`, `camply test-notifications`, and `PUSHOVER_*` / `NTFY_*` environment variables) with in-memory and optional `--state-file` seen-opening deduplication (`US2`).
3. Add `--limit` pagination beyond 50 results on live upstream discovery (`camply campgrounds`, `camply recreation-areas`) and canonical provider name support on `camply db metadata` (`US3`).
4. Add `--search-once`, `--interval`, and `--json` stdout formatting with strict stdout/stderr separation (`US4`).

## Technical Context

**Language/Version**: Python >=3.11 (default 3.14)
**Primary Dependencies**: `click`, `pydantic` v2, `pydantic-settings`, `httpx2`, `jiter`, `rich`, `structlog` (all in base package dependencies)
**Storage**: Stateless by default; optional user-specified local JSON file (`--state-file`) for single-pass notification deduplication
**Testing**: `pytest`, `click.testing.CliRunner`, synthetic `httpx2.MockTransport`, and isolated base-wheel subprocess packaging tests (`tests/packaging/`)
**Target Platform**: Linux, macOS, and Windows terminal environments (`camply-web` base wheel without extras)
**Project Type**: CLI and shared core library (`src/camply/cli/` + `src/camply/core/`)
**Performance Goals**: Zero database queries for discovery, availability, or notifications; zero duplicate upstream requests per target per cycle
**Constraints**: Must obey Import Linter layer and optional-free contracts (`cli | server | worker` → `core` → `notifications | providers` → `db` → `__about__`); secret tokens read exclusively from environment variables and never logged
**Scale/Scope**: 26 registered providers across 4 provider families (`RecreationGovProvider`, `UseDirectProvider`, `GoingToCampProvider`, `ReserveAmericaProvider`)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

1. **I. Reliability & Precision**: PASS — Site-attribute filters fail closed on unknown attributes (`is_electric is True`, `is_accessible is True`, `max_vehicle_length >= min_rv_length`), matching `camply.db.availability.matches_scan_filters` identically. Seen-opening deduplication updates only on successful poll cycles so provider failures never trigger false reopen alerts.
2. **II. Type Safety & Static Analysis**: PASS — All new CLI options, core models, and notification helpers use strict Python type annotations verified by `mypy` and linted by `ruff`.
3. **III. Modern Workflow & Automation**: PASS — All verification runs through `task` entrypoints (`task fix`, `task lint`, `task check`, `task test`, `task docs:check`).
4. **IV. Monorepos & Separation of Concerns**: PASS — All changes stay within `src/camply/cli/` and `src/camply/core/` (reusing existing base-layer `src/camply/notifications/` and `src/camply/providers/`). No `server`, `distributed`, `postgres`, or `sentry` dependencies are imported.
5. **V. Automated Verification**: PASS — Unit, Click runner, synthetic HTTP, and installed base-wheel packaging tests cover all new options, filters, notifications, deduplication, and JSON output.

## Project Structure

### Documentation (this feature)

```text
docs/specs/20261117-193928-cli-fullstack-parity/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md  # Spec quality checklist
├── contracts/
│   └── cli-contract.md  # CLI command, option, and JSON output contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (affected areas)

```text
src/camply/
├── cli/
│   ├── main.py              # Register lazy test-notifications command
│   ├── options.py           # Shared --limit, --json, filter, run-mode, and notification options
│   ├── notifications.py     # CLINotificationConfig, test_notifications_cmd, deduplicated alert sender & state-file I/O
│   ├── campsites.py         # Wire site/equipment/campsite filters, --search-once, --interval, --notifications, --state-file, --json
│   ├── campgrounds.py       # Wire --limit and --json
│   ├── recreation_areas.py  # Wire --limit and --json
│   ├── providers.py         # Wire --json and filter capability rendering
│   ├── discovery.py         # Parameterize discovery limit & truncation probe (limit + 1)
│   ├── output.py            # Render provider filter capabilities, JSON stdout serializers, and stderr-only log mode when --json is set
│   └── db.py                # Accept canonical provider names as well as numeric IDs in `camply db metadata`
└── core/
    └── search.py            # Extend SearchRequest & _stays() with campsites, campsite_types, require_electric, require_accessible, min_rv_length, and single-pass support

docs/
└── cli.md                   # Update user-facing CLI documentation with new filters, notifications, and options

tests/
├── cli/
│   ├── test_main.py             # Root routing, lazy commands, and canonical provider names in `camply db metadata`
│   ├── test_notifications.py    # test-notifications, Pushover/ntfy delivery, in-memory & state-file deduplication, secret redaction
│   └── test_search.py           # Site/equipment/campsite filters, capability validation, --limit, --search-once, --interval, --json
├── core/
│   └── test_search.py           # Unit tests for site_matches_request, SearchRequest validation, and monitor(once=True)
└── packaging/
    └── test_cli_search.py       # Installed base-wheel regression coverage for new flags and notifications
```

**Structure Decision**: Extend the existing modular `src/camply/cli/` command layout and `src/camply/core/search.py` adapter established in [CLI parity](../20261110-005958-cli-parity/plan.md), adding one focused module (`src/camply/cli/notifications.py`) for stateless Pushover/ntfy configuration, `test-notifications`, and seen-stay deduplication.

## Architecture & Phase Design

### Phase 0: Outline & Research

Completed in [research.md](research.md). Key decisions:

- **Filter parity in `camply.core.search`**: Evaluate `campsites`, `campsite_types`, `require_electric`, `require_accessible`, and `min_rv_length` directly on `CampsiteDTO` in `_stays()`, matching `camply.db.availability.matches_scan_filters` without ORM overhead.
- **Upfront capability check**: Validate requested filters against `provider_class.filter_capabilities` before resolving targets or issuing availability requests.
- **Stateless notifications & deduplication**: Reuse `camply.notifications.pushover.PushoverProvider` and `camply.notifications.ntfy.NtfyProvider` (already in the base package layer); read secret tokens strictly from environment variables; deduplicate stays by `"{provider_id}:{campground_id}:{campsite_id}:{arrival}:{checkout}"` in memory and optionally in `--state-file`.
- **Clean JSON stdout**: Route all Rich/Python log handlers to `stderr` when `--json` is passed so `stdout` contains only valid JSON.

### Phase 1: Design & Contracts

Completed in [data-model.md](data-model.md), [contracts/cli-contract.md](contracts/cli-contract.md), and [quickstart.md](quickstart.md).

**Post-Design Constitution Check**: Re-verified all five principles after finalizing `data-model.md` and `contracts/cli-contract.md`:

- Zero database migrations or server/worker dependencies introduced.
- Import Linter contracts (`Component dependency layers`, `Base dependencies stay optional-free`, and `Package root stays lightweight`) remain 100% satisfied without adding any `ignore_imports` exceptions.

## Complexity Tracking

_No Constitution Check violations exist; table omitted._
