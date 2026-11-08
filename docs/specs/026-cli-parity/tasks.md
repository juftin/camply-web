# CLI parity delivery backlog

**Status**: Specification complete; implementation tasks below are pending. IDs reference [requirements](spec.md) and [inventory](legacy-audit.md). These are delivery slices; detailed code-level tasks follow contract design for each slice.

## Foundations

- [x] T001 Audit pinned upstream release, command/option/YAML/environment surface, provider/deployment/channel coverage and known discrepancies.
- [x] T002 Specify acceptance scenarios, deliberate differences, architectural constraints, staged delivery and validation gates.
- [ ] T003 Freeze sanitized contract fixtures for C01–C12/S01–S16, YAML/JSON imports, 19 provider aliases, 17 deployment selectors and 10 channels (FR-001–018, SC-001).
- [ ] T004 Design typed requests, capabilities, stay/slot results and public provider resolution/site/equipment contracts (FR-002–004, FR-013).
- [ ] T005 Extract shared core, update architecture/governance/import contracts, and verify optional-free/negative boundary regressions before connecting CLI (FR-017–018, SC-004/006).

## First useful delivery: discovery and one-pass search

- [ ] T006 Add lazy legacy commands, module entrypoint, provider aliases, help/debug/plain rendering and truthful capability listing; protect serve/db behavior (C01–C08, FR-001–003/015).
- [ ] T007 Implement complete area/site/ID target resolution, public catalogs, paired windows, weekday union, exact-length stays and equipment filters for registered providers (S01–S06/S13–S14, FR-003–004).
- [ ] T008 Verify fresh base-wheel discover/search and invalid-input preflight with synthetic upstreams, no catalog/database/services (SC-002/004/006).

## Monitoring and configuration delivery

- [ ] T009 Implement foreground modes, effective pacing, bounded retry/concurrency, expiry, signals and exit statuses (S07–S12, FR-005–006/016).
- [ ] T010 Implement YAML compatibility/repairs and masked `.camply` resolver/wizard (C10, S15, FR-009–010).
- [ ] T011 Implement JSON import/history, per-channel outcomes, atomic save/single-writer guard, lifetime deduplication and pickle rejection guidance (S16, FR-007–008).
- [ ] T012 Share Pushover delivery with explicit token migration, booking links, 5/20 caps, test notifications and sanitized terminal error events (C11, FR-007/010–012).
- [ ] T013 Verify fake-clock mode matrix, cron restart suppression, partial delivery failures, corrupt/concurrent state and shutdown within five seconds (SC-003/005).

## Remaining interface and channel delivery

- [ ] T014 Implement/verify silent, email, ntfy, Apprise, Pushbullet, Slack, Telegram, Twilio and generic webhook compatibility, including multi-recipient/payload/error contracts (FR-011–012).
- [ ] T015 Add optional TUI with command preview, shared validation and missing-extra guidance; verify installed extras in isolation (C12, FR-014/017).

## Full provider parity gate

- [ ] T016 Verify/restore Alabama and Maricopa endpoints through feature 007; implement corresponding capabilities and contracts (FR-013).
- [ ] T017 Verify/implement Yellowstone facility inventory, legacy string-ID mappings, booking URLs and provider-specific pacing (FR-013).
- [ ] T018 Implement GoingToCamp compatibility facade and verify every legacy deployment, with public equipment/catalog contracts and native park translation (FR-002–004/013).
- [ ] T019 Implement all four Recreation.gov ticket/timed-entry variants, slot/quantity constraints and inventory-aware output/notification contracts (FR-013).
- [ ] T020 Publish migration/coverage documentation and safe install/cron/container examples; preserve current package/image names and state intentional differences (SC-001).
- [ ] T021 Run full quality, installed wheel/sdist, Python 3.11/3.14, docs and web/standalone/distributed regression gates; claim full parity only after every required gap is closed (SC-001–006).
