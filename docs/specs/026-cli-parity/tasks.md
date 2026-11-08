# CLI parity delivery backlog

**Status**: Initial implementation. Scope is limited to current-provider discovery and console-only campground availability. D01–D13 are tracked TODOs, not queued implementation slices or initial release prerequisites. See [specification](spec.md), [inventory](legacy-audit.md) and [design outline](plan.md).

## Specification work

- [x] T001 Audit the pinned legacy CLI, YAML/environment/state surface and provider/deployment/channel coverage.
- [x] T002 Define requirements and acceptance scenarios, preserving the full historical inventory.
- [x] T022 Separate initial scope from explicitly deferred TODOs; record search-forever direction without settling run-mode design.
- [x] T023 Specify the approved command tree, exact initial option/default/precedence contract, installed-command monitoring/cleanup gates and console-only scope following review. Pushover is explicitly deferred, so initial CLI credential configuration is unnecessary.

## Initial implementation backlog

- [x] T003 Create public Click command fixtures for the complete command contract: provider/debug/environment precedence, repeated IDs/date pairs/days, selector precedence, exact metadata lookup, display limits, date/stay matching, output streams and errors; deferred entries need dispositions, not runtime fixtures (FR-001–004/015, SC-001).
- [x] T004 Design typed requests and current-provider exact campground metadata lookup and exhaustive area resolution, extending feature 025 where its limited search contract is insufficient; no site/equipment/permit/history contracts (FR-002–004).
- [x] T005 Extract only shared code needed by this scope; update architecture/import contracts and optional-free regressions without adding deferred-feature abstractions (FR-017–018).
- [x] T006 Add lazy initial commands, compatible current-provider selection, plain Click help/debug/output and truthful capability listing; preserve serve/db (FR-001–003/015).
- [x] T007 Implement complete area/campground target enumeration, paired windows, weekday union and exact-length stays (FR-003–004).
- [x] T008 Verify the actual installed `camply` executable outside the checkout from base wheel/sdist-rebuilt wheel, using synthetic upstreams: supplied arguments reach provider requests, stays are printed, matching checks are followed by another cycle, and signal cancellation closes owned resources. Cover no catalog/database/services, preflight and provider failures; internal-only tests do not satisfy this task (SC-002–005).
- [x] T009 Implement immediate first check and continued checking after empty/matching responses until cancellation, with existing provider pacing and resource cleanup; verify through public entrypoint tests. Leave the three legacy switches and detailed mode/cron design to D11; no legacy mode restoration (FR-005–006/016).
- [x] T024 Verify console-only output with absent/malformed notification settings and zero notification-service requests, web-user lookup or delivery dispatch; reject `--notifications`/`test-notifications` and preserve existing web Pushover behavior (FR-010–012).
- [x] T020 Publish initial coverage, unsupported/deferred features and safe package setup examples; no deferred flag/YAML/cron examples in initial guidance (SC-001).
- [x] T021 Run relevant quality, installed wheel/sdist, Python 3.11/3.14, docs and existing serve/db/web/worker gates for initial scope (SC-001–006).

Original broader implementation tasks T010–T012 and T013–T019 are superseded by the TODO registry below. They do not schedule future implementation automatically.

## Deferred TODO registry

All entries below are TODOs; do not implement yet.

- [ ] D01 TODO: `list-campsites` and supporting site catalogs.
- [ ] D02 TODO: Search by campsite ID and site-to-parent resolution.
- [ ] D03 TODO: All external CLI notifications including Pushover, activation/recipient credentials, full provider parity, adapters and test-notifications. Initial CLI is console-only.
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
