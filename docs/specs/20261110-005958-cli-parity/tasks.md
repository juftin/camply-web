# CLI parity delivery backlog

**Status**: Initial implementation. Scope is limited to current-provider discovery and console-only campground availability. D01–D13 are tracked TODOs, not queued implementation slices or initial release prerequisites. See [specification](spec.md), [inventory](legacy-audit.md) and [design outline](plan.md).

## Specification work

- [x] T001 Audit the pinned legacy CLI, YAML/environment/state surface and provider/deployment/channel coverage.
- [x] T002 Define requirements and acceptance scenarios, preserving the full historical inventory.
- [x] T022 Separate initial scope from explicitly deferred TODOs; record search-forever direction without settling run-mode design.
- [x] T023 Specify the approved command tree, exact initial option/default/precedence contract, installed-command monitoring/cleanup gates and console-only scope following review. Pushover is explicitly deferred, so initial CLI credential configuration is unnecessary.

## Initial implementation backlog

- [x] T003 Create public Click command fixtures for the complete command contract: provider/debug/environment precedence, repeated IDs/date pairs/days, selector precedence, exact metadata lookup, display limits, date/stay matching, output streams and errors; deferred entries need dispositions, not runtime fixtures (FR-001–004/015, SC-001).
- [x] T004 Design typed requests and current-provider exact campground metadata lookup and exhaustive area resolution, extending direct upstream provider search where its limited search contract is insufficient; no site/equipment/permit/history contracts (FR-002–004).
- [x] T005 Extract only shared code needed by this scope; update architecture/import contracts and optional-free regressions without adding deferred-feature abstractions (FR-017–018).
- [x] T006 Add lazy initial commands, compatible current-provider selection, plain Click help/debug/output and truthful capability listing; preserve serve/db (FR-001–003/015).
- [x] T007 Implement complete area/campground target enumeration, paired windows, weekday union and exact-length stays (FR-003–004).
- [x] T008 Verify the actual installed `camply` executable outside the checkout from base wheel/sdist-rebuilt wheel, using synthetic upstreams: supplied arguments reach provider requests, stays are printed, matching checks are followed by another cycle, and signal cancellation closes owned resources. Cover no catalog/database/services, preflight and provider failures; internal-only tests do not satisfy this task (SC-002–005).
- [x] T009 Implement immediate first check and continued checking after empty/matching responses until cancellation, with existing provider pacing and resource cleanup; verify through public entrypoint tests. Leave the three legacy switches and detailed mode/cron design to D11; no legacy mode restoration (FR-005–006/016).
- [x] T024 Verify console-only output with absent/malformed notification settings and zero notification-service requests, web-user lookup or delivery dispatch; reject `--notifications`/`test-notifications` and preserve existing web Pushover behavior (FR-010–012).
- [x] T020 Publish initial coverage, unsupported/deferred features and safe package setup examples; no deferred flag/YAML/cron examples in initial guidance (SC-001).
- [x] T021 Run relevant quality, installed wheel/sdist, Python 3.11/3.14, docs and existing serve/db/web/worker gates for initial scope (SC-001–006).
- [x] T025 Split CLI commands/groups into focused modules, centralize shared Click options and isolate execution/discovery/output helpers. Preserve lazy loading, option precedence and existing command contracts through the CLI/import and installed-package regressions.

Original broader implementation tasks T010–T012 and T013–T019 are superseded by the TODO registry below. They do not schedule future implementation automatically.

## Deferred TODO registry

Status of the D01–D13 legacy inventory items across CLI full-stack parity, CLI YAML configuration, and the modern CLI completion:

- [x] D01 Implemented: `camply list-campsites` and provider site-catalog APIs across all 26 providers (Recreation.gov, UseDirect, GoingToCamp, ReserveAmerica) with `--search`, site-attribute filters, `--limit`, and `--json`.
- [x] D02 Implemented (CLI full-stack parity): `--campsite` ID/name filtering within selected `--campground` / `--rec-area` targets.
- [x] D03 Implemented (CLI full-stack parity + modern channels): `pushover`, `ntfy`, `webhook`, `discord`, `slack`, and `telegram` channels with `camply test-notifications`, env-var credentials, and secret redaction. Legacy `email`, `twilio`, `pushbullet`, `apprise`, and `silent` channels intentionally dropped.
- [x] D04 Completed for verified live providers: all 26 current providers (Recreation.gov, 10 UseDirect, 14 GoingToCamp, ReserveAmerica); retired/migrated legacy providers (Yellowstone/Xanterra, Alabama, Maricopa) closed out.
- [x] D05 Implemented (CLI YAML configuration): `version: 2` multi-search/multi-provider `--yaml-config` with strict validation, shared defaults, JSON Schema, and per-search overrides.
- [ ] D06 TODO (roadmap): Permits and non-camping inventory (tracked separately in `docs/PLAN.md`).
- [x] D07 Implemented (CLI full-stack parity): `--campsite-type`, `--electric`, `--accessible`, `--rv-length` and provider capability validation.
- [x] D08 Dropped (intentional): Legacy Trogon TUI dropped; `camply serve` provides the full interactive web UI.
- [x] D09 Dropped (intentional): `rich-click` dropped; plain Click + `CamplyRichHandler` avoids extra dependency bloat.
- [x] D10 Dropped (intentional): `configure` wizard and implicit `~/.camply` dotenv file dropped to keep the CLI stateless with explicit env vars and `camply.yaml`.
- [x] D11 Implemented (redesigned): Continuous watch is the default with transient-error retries and automatic date-expiry stop; `--search-once` for single-pass checks, `--stop-on-match` to stop on first match, and `--interval` (>= 5 min). Legacy `--continuous` and `--search-forever` intentionally dropped.
- [x] D12 Implemented (redesigned): Replaced `--notify-first-try` and hidden 5/20 caps with explicit `--max-notifications` (1–100, default 5; also in YAML) and automatic overflow summary alerts.
- [x] D13 Implemented (CLI full-stack parity / YAML config): Stateless in-memory deduplication plus explicit JSON `--state-file` / YAML `state_file` persistence; legacy pickle state dropped.
