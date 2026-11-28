# Tasks: Recreation-area and selected-campground monitoring

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/scans.md), [validation guide](quickstart.md).

**Status**: Implementation completed for T001–T043 (Docker-only PostgreSQL/admin/healthcheck container suites skipped locally because Docker daemon is unavailable; see `quickstart.md` for tool baseline and environment limits). Ready for `/speckit-converge` (`T044`).

**Tests**: Required by the specification and constitution. Write the relevant behavior regression first and observe its failure before implementing each slice. Use only synthetic provider and delivery data. Existing Task wrappers remain the command entrypoints.

**Format**: `- [ ] T### [P?] [US#?] Description with file paths`. `[P]` means independent files within the stated phase after its prerequisites, not permission to skip test-first ordering. New paths below are planned files, not existing implementation.

## Phase 1: Setup

- [x] T001 Record the implementation baseline and installed tool versions in `docs/specs/20261115-200611-recreation-area-monitoring/quickstart.md` using `task lint`, `task check`, `task test`, and `task api:check`; document pre-existing failures before source edits.
- [x] T002 Add reusable synthetic provider/area/campground/site fixtures and a controlled clock in `tests/conftest.py`, including repeated native IDs across providers and campgrounds, empty areas, 125 members, and independent user preferences; keep credentials out of fixtures.

## Phase 2: Foundation (blocks all stories)

- [x] T003 [P] Add populated SQLite migration/backfill, duplicate-preflight, FK integrity, downgrade/refusal and re-upgrade regressions in `tests/db/test_area_scan_migration.py`; preserve scan/target/result IDs, timestamps, preferences and pending legacy intents. (FR-016)
- [x] T004 [P] Add canonical definition, overlap, unavailable selection, membership publication race and shared-subscriber query regressions in `tests/db/test_scan_coverage.py`; enforce fixed subset identity independent of order, repeats, labels and preferences. (FR-004–FR-010)
- [x] T005 Generalize `src/camply/db/models/user_scans.py` with the exact fields/checks from `data-model.md`: kind `campground`/`recreation_area`, `String(128), nullable` destination IDs, `String(255), non-null` last known name, nullable mode `all`/`selected`, `JSON, non-null, default []` fixed choices with nonempty IDs of at most 128 characters, scan-owned dates with `end_date > start_date`, `String(64), non-null` hash and unique `(user_id, definition_hash)`, positive definition/coverage/row versions, and nullable current-round UUID/timestamps. Keep existing preferences and the nullable campground-only target pointer. (FR-001, FR-009, FR-016)
- [x] T006 Add `src/camply/db/models/scan_targets.py` and register it in `src/camply/db/models/__init__.py`; use `scan_id, target_id` as composite primary key with scan-link cascade only, positive coverage revision, nullable round/attempt UUIDs and outcome times, outcomes `pending`, `retrying`, `success`, `failed`, and nullable `String(64)` sanitized error. Add latest nullable attempt UUID/times/error to `unique_targets.py` and nonnegative `catalog_revision` default 0 to `providers.py`; preserve existing target hash and composite campground FK. (FR-004, FR-010, FR-013)
- [x] T007 Extend `src/camply/db/models/notification_outbox.py` with `payload_kind` String(24) default `campground`, values `campground`/`area`, nullable positive scan revision and positive payload version default 1; retain existing lifecycle/unique keys and legacy payload readability. Cover exact data-model constraints in `tests/db/test_models.py`. (FR-014–FR-016)
- [x] T008 Generate and review a real revision under `src/camply/db/migrations/versions/` using `task backend:migration`; implement the documented duplicate preflight, backfill, named constraints, SQLite inbound-FK-safe batch changes and guarded downgrade. Extend `tests/db/test_postgres_migrations.py` and installed-resource checks in `tests/packaging/` for both migration paths. (FR-016)
- [x] T009 Implement canonical identity, transactional target/link reconciliation, provider-revision/scan-version guards, and association-aware eligibility/subscriber helpers in `src/camply/db/coverage.py`; preserve all unavailable fixed IDs/names without cascading catalog references. Update `src/camply/db/eligibility.py` consumers to use one common eligibility definition. (FR-004–FR-010)
- [x] T010 Add failed-second-dataset, complete-removal, malformed-input and post-commit enrichment regressions in `tests/providers/test_recreation_gov.py`, `tests/providers/test_recreation_gov_models.py` and `tests/worker/test_ingestion.py`; assert incomplete catalog work does not publish changed membership. (FR-005)
- [x] T011 Make Recreation.gov metadata/search publication atomic in `src/camply/providers/recreation_gov/provider.py` and `models/recreation_area.py`/`models/campgrounds.py`; validate both complete datasets before writes, remove helper-owned commits and soft-disable confirmed absent rows. Increment provider revision in the same complete transaction for Recreation.gov, `src/camply/providers/usedirect/provider.py` and `src/camply/providers/going_to_camp/provider.py`. Keep post-publication enrichment independent in `src/camply/worker/engine/catalog.py`. (FR-005)

**Checkpoint**: Portable backfill and confirmed membership pass before user-story code. No area-aware worker may ship while remaining consumers still rely on a single target.

## Phase 3: US1 — Monitor every campground (P1)

**Goal**: One all-area scan resolves the complete eligible membership and reuses shared campground checks.

**Independent test**: Save an all-area scan covering 125 eligible members, confirm one saved subscription, then add/remove catalog members and verify the next round's coverage without extra per-user checks.

- [x] T012 [P] [US1] Add all-area create/list/detail and legacy campground contract regressions in `tests/server/routers/test_area_scans.py`; cover unknown/disabled/empty areas, conflicting fields, dates/minimum stay, complete membership and 401/403/ownership/CSRF. (FR-001–FR-007, FR-016; SC-001)
- [x] T013 [P] [US1] Add ten-user/three-target, 125-member paging, cooldown reuse, in-flight dedup and next-round membership regressions in `tests/worker/test_area_coverage.py`, for standalone and distributed discovery adapters. (FR-005, FR-010, FR-017; SC-001, SC-004)
- [x] T014 [US1] Add compatible destination request variants and response identity/count fields in `src/camply/server/schemas.py`; extend `src/camply/server/routers/scans.py` to create/read one all-area definition and resolved links atomically with canonical duplicate handling. Preserve legacy campground writes and real scalar campground identity. (FR-001, FR-006–FR-007, FR-009, FR-016)
- [x] T015 [US1] Implement current-round opening and complete all-membership reconciliation in `src/camply/worker/engine/coverage.py`; use captured link membership, current UUID/revision guards and fresh shared observations without forcing checks before cooldown. (FR-004–FR-005, FR-010, FR-013)
- [x] T016 [US1] Convert due discovery and scanner subscriber loading in `src/camply/worker/engine/discovery.py`, `engine/scanner.py`, `tasks/heartbeat.py` and `runtime.py` to association-aware live eligibility; page 100 distinct targets, prevent queued/in-flight duplicates, and retain provider cooldown/locks and no-page-read provider I/O. (FR-010, FR-017; SC-004)
- [x] T017 [US1] Add area destination types and all-mode form handling in `src/frontend/lib/structs.ts`, `lib/api.ts`, `hooks/useScans.ts` and `components/ScanForm.tsx`; regenerate `lib/api/generated/schema.ts` through `task api:generate` after schemas settle and check it with `task api:check`. (FR-001–FR-002, FR-016)
- [x] T018 [US1] Add area Monitor actions to `src/frontend/pages/RecreationArea.tsx`, `pages/SearchPage.tsx`, `components/ExploreMap.tsx` and the form picker; show provider, area, full eligible count, all-mode membership explanation and actionable unavailable states. Add regressions first in their colocated tests and `components/ScanForm.test.tsx`. (FR-002, FR-007, FR-018)

**Checkpoint**: All-area coverage works as a development increment. Full attributed results, delivery and management release gates remain US3/US4; do not release incomplete area alerts.

## Phase 4: US2 — Select campgrounds within the area (P1)

**Goal**: Save one fixed selection, independent of catalog additions and the displayed search page.

**Independent test**: Select A/C from four members, search/page away and save; add E and temporarily disable C, verifying stable choices, no E coverage and visible C recovery.

- [x] T019 [P] [US2] Add paginated eligible-choice regressions in `tests/server/routers/test_monitoring_campgrounds.py`, covering complete eligible counts, query/paging, deterministic order, provider scoping, empty/disabled areas, and unchanged original child metadata route. (FR-003–FR-004, FR-018)
- [x] T020 [P] [US2] Add fixed-selection creation/update validation and normalization regressions in `tests/server/routers/test_area_scan_selection.py`; cover one member, all-current explicit selection, repeated/order-varied IDs, empty/new invalid members, retained unavailable choices and atomic cross-area/provider rejection. (FR-003–FR-006, FR-009; SC-002)
- [x] T021 [US2] Add `GET /rec-area/{provider}/{id}/monitoring-campgrounds` in `src/camply/server/routers/recreation_areas.py` with query default empty, limit default 50/range 1–100, offset default 0/nonnegative, name/ID order, filtered total, eligible total and catalog revision. Keep the existing `/campgrounds` response unchanged. (FR-003–FR-004)
- [x] T022 [US2] Implement fixed-choice validation and eligible intersection through `src/camply/db/coverage.py` and `src/camply/server/routers/scans.py`; preserve saved unavailable labels, require explicit choices on all→selected, clear them on selected→all, and revalidate destination replacement without carrying old IDs. (FR-003–FR-006, FR-008–FR-009)
- [x] T023 [US2] Add subset form regressions before UI changes in `src/frontend/components/ScanForm.test.tsx` and `ScanForm.dates.test.tsx`, including selection beyond page one, filtering without lost choices, mode/destination resets, keyboard use and failed-save draft retention. (FR-003, FR-006, FR-018; SC-007)
- [x] T024 [US2] Implement eligible-choice querying and provider/area-qualified draft selection in `src/frontend/lib/api.ts`, `lib/structs.ts` and `components/ScanForm.tsx`; show selected names/count, remove controls, unavailable retained choices, loading/query-empty/error states and nonempty validation. Update generated types after route additions. (FR-003, FR-006, FR-018)

**Checkpoint**: New members join all mode only; a subset containing every current member remains fixed selected coverage. Run US1 regressions again.

## Phase 5: US3 — Attributed results, truthful coverage and alerts (P1)

**Goal**: Combine matching openings safely, show partial coverage and send timely summaries with qualified booking destinations.

**Independent test**: Two included campgrounds share site `001`, one member fails, and another is excluded. Prove independent stays/counts/links, stale labeling, unchanged/reopened alert semantics, one intent per window and healthy delivery within 60 seconds.

- [x] T025 [P] [US3] Add qualified-site result/count/filter/stay regressions in `tests/server/routers/test_scan_results.py` and `tests/db/test_availability.py`, including expired/separated nights, metadata failure and no cross-site/campground combination. (FR-011–FR-012; SC-003)
- [x] T026 [P] [US3] Add area summary/direct, concurrent append/claim, window boundary, retry, crash/restart and pre-send eligibility regressions in `tests/worker/test_area_alerts.py`; fake healthy delivery must meet 60 seconds and preserve legacy summary/direct behavior. (FR-014–FR-017; SC-005)
- [x] T027 [US3] Extend `tests/worker/test_area_coverage.py` first for 90-second attempt timeout, four-attempt policies, lease validation, pending/retrying/failed statuses, absolute round deadlines, interrupted recovery and stale callbacks after membership/edit changes. (FR-013–FR-014, FR-017; SC-005)
- [x] T028 [US3] Aggregate matching per target before union in `src/camply/db/availability.py` and `src/camply/server/routers/scans.py`; add provider/campground/site-qualified result identity, names, URLs, freshness, current-round counts and last full success without fabricated area campground IDs. (FR-007, FR-011–FR-014)
- [x] T029 [US3] Persist attempt and member outcomes/full success in `src/camply/worker/engine/coverage.py` and `engine/scanner.py`; apply revision/round/attempt guards, snapshot/intent atomicity and independent failure retention. Add 90-second budgets and lock lease >=105-second validation in `config.py`, and adapter timeout/retry/recovery handling in `runtime.py` and `tasks/scanner.py`, including correcting swallowed distributed retry requests. (FR-010, FR-013–FR-014, FR-017)
- [x] T030 [US3] Implement area summary candidate creation/merge in `src/camply/worker/engine/area_alerts.py` and integrate it with `engine/scanner.py`: deterministic five-second window identity, qualified candidates, payload-version compare-and-swap, sealed-window rules and credential-free durable intents. Keep campground dispatch unchanged. (FR-014–FR-016)
- [x] T031 [US3] Extend `src/camply/worker/outbox.py` and `engine/notifications.py` for atomic area claims, 45-second claim leases, 30-second send budget, per-candidate current-revision/membership/filter/access/channel checks, empty-summary skips, expired-lease recovery and existing finite retries/pruning. Support qualified area direct alerts while retaining old target/payload guards. (FR-008, FR-014–FR-016)
- [x] T032 [US3] Wire one-second area outbox discovery independent of availability heartbeat in `src/camply/worker/runtime.py`, `celery_app.py` and `tasks/notifications.py`; prevent duplicate legacy dispatch, emit existing structured outcome telemetry, and test restart/live-claim behavior in `tests/worker/test_runtime.py` and `test_distributed_dispatch.py`. (FR-015, FR-017; SC-005)
- [x] T033 [US3] Add result UI regressions first in `src/frontend/components/FoundCampsites.test.tsx` and `pages/ScanDetail.test.tsx`, then update `FoundCampsites.tsx`, `pages/ScanDetail.tsx` and scan types to use qualified keys/counts, campground-name search, area metadata/provider links, bounded stay-group display and honest pending/failed/stale results. (FR-011–FR-013, FR-018; SC-003, SC-007)

**Checkpoint**: Successful children remain useful during another child's failure. No expired/excluded/unchanged observation invents a new opening, and summaries do not wait for full-area completion.

## Phase 6: US4 — Manage one scan and preserve other subscribers (P2)

**Goal**: Complete lifecycle, dashboard/admin representation and overlap isolation for both destination kinds.

**Independent test**: With two users and overlapping all/subset/campground scans, edit/pause/delete one scan; verify stable scan identity, current coverage, unaffected other scans and continued shared checks where needed.

- [x] T034 [P] [US4] Add lifecycle, destination/mode/date changes, definition uniqueness races, concurrent-edit conflicts, suspension/ownership and post-edit stale-delivery regressions in `tests/server/routers/test_scan_editing.py` and `test_suspension_regression.py`. (FR-006, FR-008–FR-010; SC-006)
- [x] T035 [P] [US4] Add saved-scan versus target count/list regressions in `tests/server/routers/test_admin.py` and `tests/server/routers/test_scans.py`, including multiple member targets, distinct linked scan counts, area target links and active/overdue/dormant eligibility. (FR-007, FR-010, FR-016)
- [x] T036 [US4] Complete merge/replacement, normalized duplicate and row-version conflict handling in `src/camply/server/routers/scans.py`; atomically update links/revisions, preserve UUID/creation/active preferences, and invalidate old pending intents on user edits or deletion without touching shared snapshots. (FR-006, FR-008–FR-010)
- [x] T037 [US4] Replace remaining direct target joins in `src/camply/server/routers/admin.py` and associated schemas with association-aware distinct counts and real member links; keep target detail campground-level and one row per saved scan. (FR-007, FR-010, FR-016)
- [x] T038 [US4] Add regressions first in `src/frontend/pages/Dashboard.test.tsx` and admin colocated tests, then update `pages/Dashboard.tsx`, `components/ScanCard.tsx`, `pages/admin/AdminScans.tsx`, `AdminScanDetail.tsx`, `AdminTargetDetail.tsx` and `AdminUserDetail.tsx` to group by qualified destination, label all/selected coverage and manage one scan with actual target links. Preserve keyboard/control/error behavior. (FR-007–FR-008, FR-018)
- [x] T039 [US4] Cover full edit round-trip, cancel/reopen, failed-save retention and unavailable pure date/preference edits in `src/frontend/components/ScanForm.test.tsx` and `pages/ScanDetail.test.tsx`; finish the matching form/detail behavior and regenerate/check types through `task api:generate` and `task api:check`. (FR-006, FR-008, FR-016, FR-018; SC-006–SC-007)

**Checkpoint**: US1–US4 acceptance is complete before cross-cutting release validation; no task checkbox is completed solely because design exists.

## Phase 7: Cross-cutting verification and documentation

- [x] T040 Extend synthetic real-runtime/browser coverage in `tests/server/integration/standalone_fixture.py`, `test_standalone_smoke.py`, `test_admin_smoke.py`, `src/frontend/tooling/standalone-live-smoke.ts` and `admin-live-smoke.ts` for both modes, 125-member completeness, overlapping users, excluded membership, restart/partial failure and healthy alert timing; run `task standalone:test`, `task admin:smoke` and `task backend:healthcheck:test`. (SC-001–SC-007)
- [x] T041 Add/inspect mobile/desktop light/dark area/subset/partial-result scenarios in `src/frontend/tooling/run-snapshots.ts`, `admin-snapshot-mocks.ts` and `tests/frontend/snapshots/baselines/`; cover keyboard selection outside page one, long labels, failed saves, login return and configured URL prefixes before accepting visual baselines. (FR-018; SC-007)
- [x] T042 Update `docs/architecture/DESIGN_DATA.md`, `DESIGN_API.md`, `DESIGN_FRONTEND.md`, `DESIGN_NOTIFICATIONS.md`, `ARCHITECTURE_DEEP_DIVE.md`, `docs/operations/CONFIGURATION.md` and `docs/development/DEVELOPER_GUIDE.md` with actual coverage, timeout/lease, alert and migration behavior; update `docs/CHECKLIST.md` and feature validation evidence only for completed work. (FR-016–FR-017)
- [x] T043 Run final gates in `docs/specs/20261115-200611-recreation-area-monitoring/quickstart.md`: `task fix`, `task lint`, `task check`, `task test`, `task api:check`, `task docs:check`, applicable pre-commit hooks and populated SQLite/PostgreSQL/installed-package checks on supported Python versions. Record results and remaining material limitations without claiming production rollout. (SC-001–SC-007; Constitution I–V)
- [ ] T044 After implementation, run `/speckit-converge` against `docs/specs/20261115-200611-recreation-area-monitoring/tasks.md`; append and execute any remaining acceptance work until `Converged`, then review stop/migrate/matched-version startup and downgrade-refusal evidence in `quickstart.md`. Do not run this task during planning. (SC-006; Constitution V)

## Dependencies and execution order

Phase 1 precedes Phase 2. Within foundation, T003/T004 are independent after fixture setup; T005–T009 follow their failing tests and schema dependencies. T010 precedes T011. All foundation tasks finish before US1.

US1 → US2 for creation integration. US3 depends on US1 target coverage and uses US2 for excluded-subset acceptance; its result/alert tests can be prepared once foundation is stable. US4 depends on the earlier definition/result/delivery contracts and finalizes lifecycle/admin consumers. Phase 7 follows all stories. Within every story, tests precede implementation; shared-file tasks run sequentially.

Concrete dependencies include T014→T017→T018, T019→T021, T020→T022, T023→T024, T025→T028→T033, T026→T030→T031→T032, T027→T029, T034→T036, T035→T037→T038, and T036→T039. Re-run earlier story acceptance after shared-module changes.

### Parallel execution examples

- **Foundation**: T003 migration tests and T004 coverage tests touch different files after T002.
- **US1**: T012 API tests and T013 worker tests can be written together after foundation; implementation follows each failing contract.
- **US2**: T019 choice-route tests and T020 selection-validation tests are independent before T021/T022. T023 UI tests can be prepared separately, but T024 waits for the finalized choice contract.
- **US3**: T025 result/filter tests and T026 alert tests are independent after coverage foundation. T027 modifies the earlier worker coverage suite and is not marked parallel with an unfinished T013.
- **US4**: T034 lifecycle tests and T035 admin/list tests are independent. T036/T037 implementations use shared schemas/query helpers and run in order.

## Requirement coverage map

| Requirement | Tasks                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| FR-001      | T005, T014, T017                                                           |
| FR-002      | T012, T017, T018                                                           |
| FR-003      | T019–T024                                                                  |
| FR-004      | T004, T006, T009, T015, T019, T021                                         |
| FR-005      | T009–T011, T013, T015, T020, T022                                          |
| FR-006      | T012, T014, T020, T022–T024, T034, T036, T039                              |
| FR-007      | T012, T014, T018, T028, T035, T037–T038                                    |
| FR-008      | T022, T031, T034, T036, T038–T039                                          |
| FR-009      | T004–T005, T009, T014, T020, T022, T034, T036                              |
| FR-010      | T004, T006, T009, T013, T015–T016, T029, T034–T037                         |
| FR-011      | T025, T028, T033                                                           |
| FR-012      | T025, T028, T033                                                           |
| FR-013      | T006, T015, T027–T029, T033                                                |
| FR-014      | T007, T026–T031                                                            |
| FR-015      | T007, T026, T030–T032                                                      |
| FR-016      | T003, T005, T007–T008, T012, T014, T017, T030–T031, T035, T037, T039, T042 |
| FR-017      | T013, T016, T026–T027, T029, T032, T040, T042–T043                         |
| FR-018      | T018–T019, T023–T024, T033, T038–T041                                      |
| SC-001      | T012–T013, T015, T040, T043                                                |
| SC-002      | T020, T022–T024, T040, T043                                                |
| SC-003      | T025, T028, T033, T040, T043                                               |
| SC-004      | T013, T016, T040, T043                                                     |
| SC-005      | T026–T032, T040, T043                                                      |
| SC-006      | T003, T008, T034–T037, T039–T040, T043–T044                                |
| SC-007      | T023–T024, T033, T038–T041, T043                                           |

T001/T002 support every story's reproducible verification; T042–T044 satisfy project documentation/governance as well as mapped requirements. There is no unrelated cleanup or dependency upgrade task.

## Implementation strategy and stop boundary

US1 is the smallest development increment; the user's requested selected-campground behavior requires US2, and the release requires US3/US4 plus final validation. Implement incrementally behind the matched-version rollout boundary, preserving campground regressions throughout. No independent deployment of partially converted worker/admin/delivery consumers is planned.

There are 44 future tasks: 2 setup, 9 foundational, 7 US1, 6 US2, 9 US3, 6 US4 and 5 cross-cutting tasks. All remain unchecked. The next phase is `/speckit-implement` only after the user chooses to begin implementation and the reviewer-owned requirements checklist has been addressed.
