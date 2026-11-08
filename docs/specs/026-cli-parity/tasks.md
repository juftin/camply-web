# CLI parity delivery backlog

**Status**: Specification only. Initial implementation is limited to current-provider discovery and campground-based availability. D01–D13 are tracked TODOs, not queued implementation slices or initial release prerequisites. See [specification](spec.md), [inventory](legacy-audit.md) and [design outline](plan.md).

## Specification work

- [x] T001 Audit the pinned legacy CLI, YAML/environment/state surface and provider/deployment/channel coverage.
- [x] T002 Define requirements and acceptance scenarios, preserving the full historical inventory.
- [x] T022 Separate initial scope from explicitly deferred TODOs; record search-forever direction without settling run-mode design.

## Initial implementation backlog

- [ ] T003 Create fixtures for initial provider listing, discovery, area/campground selectors, date/day/stay matching and errors; deferred entries need dispositions, not runtime fixtures (FR-001–004/015, SC-001).
- [ ] T004 Design typed requests and current-provider campground/area resolution using existing discovery/availability capabilities; no site/equipment/permit/history contracts (FR-002–004).
- [ ] T005 Extract only shared code needed by this scope; update architecture/import contracts and optional-free regressions without adding deferred-feature abstractions (FR-017–018).
- [ ] T006 Add lazy initial commands, compatible current-provider selection, plain Click help/debug/output and truthful capability listing; preserve serve/db (FR-001–003/015).
- [ ] T007 Implement complete area/campground target enumeration, paired windows, weekday union and exact-length stays (FR-003–004).
- [ ] T008 Verify fresh base-wheel discovery/internal availability checks, invalid-input preflight, no catalog/database/services, and provider failure handling (SC-002–005).
- [ ] T009 Use search-forever as the default direction for initial availability, with existing provider pacing and resource cleanup. Leave the three legacy switches and detailed mode/cron design to D11; no legacy mode restoration (FR-005–006/016).
- [ ] T012 Reuse current Pushover capability and environment settings where needed, with direct booking links and visible failures. Additional channels, legacy caps and configure are excluded (FR-010–012).
- [ ] T020 Publish initial coverage, unsupported/deferred features and safe package setup examples; no deferred flag/YAML/cron examples in initial guidance (SC-001).
- [ ] T021 Run relevant quality, installed wheel/sdist, Python 3.11/3.14, docs and existing serve/db/web/worker gates for initial scope (SC-001–006).

Original broader implementation tasks T010–T011 and T013–T019 are superseded by the TODO registry below. They do not schedule future implementation automatically.

## Deferred TODO registry

All entries below are TODOs; do not implement yet.

- [ ] D01 TODO: `list-campsites` and supporting site catalogs.
- [ ] D02 TODO: Search by campsite ID and site-to-parent resolution.
- [ ] D03 TODO: Full notification provider parity, additional adapters and multi-channel test-notification compatibility.
- [ ] D04 TODO: Full campground parity, missing providers/catalogs and broader GoingToCamp deployment mappings.
- [ ] D05 TODO: YAML files, aliases, schema/defaults, environment expansion and precedence.
- [ ] D06 TODO: Permits and non-camping inventory, including legacy ticket/tour/timed-entry variants.
- [ ] D07 TODO: Equipment filtering and equipment lookup/category/length capabilities.
- [ ] D08 TODO: TUI.
- [ ] D09 TODO: Rich-click.
- [ ] D10 TODO: Configure command and legacy `.camply` import/write behavior.
- [ ] D11 TODO: Brainstorm `--continuous` / `--search-forever` / `--search-once`; intended default is search forever. Flags, cron, stopping behavior, pacing and notification suppression remain open.
- [ ] D12 TODO: `--notify-first-try` and legacy notification caps.
- [ ] D13 TODO: `--offline-search`, `--offline-search-path`, persistent JSON history/import and cross-process duplicate suppression.

Bring each TODO into scope explicitly before creating detailed implementation tasks or acceptance gates for it.
