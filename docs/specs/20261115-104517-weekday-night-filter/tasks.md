# Tasks: Nights of the week

**Input**: [spec](spec.md), [plan](plan.md), [research](research.md), [data model](data-model.md), [contracts](contracts/night-selection.md).

**Tests**: Required by constitution; write behavioral regressions and observe failure before corresponding implementation. All work stays in existing layers.

## Phase 1: Setup

- [x] T001 Review clarification coverage, architecture, constitution, and existing behavior in docs/specs/20261115-104517-weekday-night-filter/research.md.
- [x] T002 Review requirements-quality checklist in docs/specs/20261115-104517-weekday-night-filter/checklists/night-selection.md and validate task/spec/plan coverage before implementation.

## Phase 2: Foundation

- [x] T003 Add failing calendar and migration regressions in tests/db/test_availability.py and tests/db/test_weekday_migration.py, covering all 127 nonempty subsets, excluded gaps, cross-week/year/leap dates, populated migration compatibility and feasibility.
- [x] T004 Add nullable JSON allowed_weekdays to src/camply/db/models/user_scans.py and an additive migration in src/camply/db/migrations/versions/; Monday=0 through Sunday=6, null means unrestricted, and preserve populated rows through upgrade/downgrade.
- [x] T005 Extend matching and calendar feasibility helpers in src/camply/db/availability.py to filter selected booking weekdays before consecutive grouping, preserving unrestricted defaults and existing site preferences (FR-003/004/005/010).

## Phase 3: User Story 1 — Seasonal weekend monitoring (P1, MVP)

**Independent test**: One June–September scan with Friday/Saturday and two-night minimum finds complete weekends only, with Sunday checkout and matching results/counts/alerts.

- [x] T006 [US1] Add failing create/results/validation and shared-target tests in tests/server/routers/test_scans.py and tests/server/routers/test_scan_results.py for strict day values, empty/omitted/all-seven selections, impossible constraints and independent subscriber results.
- [x] T007 [US1] Add validated nonempty strict integer weekday lists and response defaults in src/camply/server/schemas.py; normalize order/duplicates, reject explicit null, and preserve omitted create/PATCH semantics (FR-007/008).
- [x] T008 [US1] Persist and expose preferences and validate merged date/stay/day criteria before mutation in src/camply/server/routers/scans.py; preserve status-only operations, duplicate rules and scan/target identity.
- [x] T009 [P] [US1] Add failing weekday detection and queued direct/summary delivery regressions in tests/worker/test_summary_alerts.py, tests/worker/test_outbox.py and tests/worker/test_notifications.py, covering edits, excluded-only changes, subscriber isolation and both runtime paths.
- [x] T010 [US1] Apply weekday matching to src/camply/worker/engine/alerts.py and current-payload revalidation to src/camply/worker/engine/notifications.py with current target linkage; preserve shared polling and unscoped test notifications (FR-009/010/012).
- [x] T011 [US1] Regenerate src/frontend/lib/api/generated/schema.ts using task api:generate after the backend contract is complete.

## Phase 4: User Story 2 — Custom nights and editing (P1)

**Independent test**: Create, reload, edit, cancel, reset and retry a custom-day scan; validate accessible selection and unchanged unrelated preferences.

- [x] T012 [P] [US2] Add failing edit/omission/reset/atomic-failure/expiration tests in tests/server/routers/test_scan_editing.py (FR-006/007/008).
- [x] T013 [P] [US2] Add failing selector, shortcuts, defaults, impossible/empty validation, persistence/edit/cancel/retry and summary tests in src/frontend/components/ScanForm.test.tsx, ScanForm.dates.test.tsx, ScanCard.test.tsx and src/frontend/pages/ScanDetail.test.tsx.
- [x] T014 [US2] Implement accessible seven-night buttons, Weekends/Any night shortcuts, saved defaults/submission and actionable validation in src/frontend/components/ScanForm.tsx; quick dates must not alter nights.
- [x] T015 [US2] Add shared night display formatting in src/frontend/lib/ and saved preference summaries in src/frontend/components/ScanCard.tsx and src/frontend/pages/ScanDetail.tsx.

## Phase 5: User Story 3 — CLI parity (P1)

**Independent test**: The CLI and saved scan matcher identify the same eligible nights for identical observations; exact CLI stays remain distinct from minimum web stay presentation.

- [x] T016 [US3] Extend parity regressions in tests/core/test_search.py and tests/cli/test_search.py for all weekday subsets, weekend-plus-Sunday union, aliases, gaps and exact stays; preserve src/camply/core/search.py behavior unless a demonstrated parity defect requires correction (FR-011, SC-002).
- [x] T017 [US3] Document equivalent summer-weekend CLI/web examples and occupied-night/stay semantics in docs/cli.md.

## Phase 6: Verification and documentation

- [x] T018 Update docs/architecture/DESIGN_DATA.md, DESIGN_API.md, DESIGN_FRONTEND.md and DESIGN_NOTIFICATIONS.md with storage, request, UI and matching/delivery contracts; update docs/CHECKLIST.md.
- [x] T019 Update and inspect affected baselines in tests/frontend/snapshots/ through the existing snapshot tooling, covering keyboard/mobile selection and saved summaries without unrelated baseline changes.
- [x] T020 Run task fix, task lint, task check, task test, task api:check and applicable migration/pre-commit checks; record outcomes and environmental limits in docs/specs/20261115-104517-weekday-night-filter/quickstart.md.
- [x] T021 Audit current implementation against docs/specs/20261115-104517-weekday-night-filter/spec.md, plan.md and tasks.md using convergence; append and implement any remaining gaps until Converged.

## Dependencies and execution order

Setup → Foundation → story integrations → verification. T003 precedes T004/T005. T006 precedes T007/T008. T009 precedes T010. T011 follows T007/T008. T012 exercises T008. T013 precedes T014/T015 and depends on the documented generated contract. T016 can run independently once foundation is complete. T018–T021 follow all story work.

## Parallel examples

- US1: worker tests/implementation (T009/T010) can run beside API tests/implementation (T006–T008), with distinct file ownership after the shared matcher contract is fixed.
- US2: frontend tests/control work (T013–T015) can run beside backend editing regressions (T012); summaries and form share a small formatting helper contract.
- US3: CLI parity tests (T016) and documentation (T017) can run beside frontend work after foundation.

## Implementation strategy

Establish the base contract and its regressions first. Deliver seasonal weekend matching as the first useful slice, then custom editing and summaries, then explicit CLI compatibility verification. Reuse existing controls and matching helpers, keep provider polling untouched, and complete all requested slices before the final convergence audit.

## Phase 7: Convergence

First audit: all 12 functional requirements, six success criteria, three user stories and five constitution principles reviewed. One partial verification gap remains: SC-001 has calendar/subscriber coverage but no single seasonal saved-scan regression. No missing application behavior was identified.

- [x] T022 [US1] Add a June 1–September 1, 2027 single-scan regression in tests/server/routers/test_scan_weekdays.py proving every supplied complete weekend is returned while midweek and isolated-night sites are excluded from details and counts (SC-001, US1).

Implementation evidence: API create/edit/result regressions are consolidated in tests/server/routers/test_scan_weekdays.py; worker regressions are consolidated in tests/worker/test_weekday_alerts.py; existing tests in the originally named files were also run. Client contract integration additionally updates src/frontend/lib/structs.ts. Required module attribute docstrings use the existing targeted check-docstring-first exclusions in .pre-commit-config.yaml.
