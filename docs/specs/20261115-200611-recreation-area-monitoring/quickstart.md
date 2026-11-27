# Validation guide: Recreation-area monitoring

**Status**: Implemented and verified against deterministic acceptance suites (Docker daemon unavailable locally; PostgreSQL migration smoke and container smokes remain for CI/Docker environments).

## Prerequisites and setup for implementation

Use the existing root development setup, Python 3.14 (also verify compatibility with 3.11), pnpm and Task. Provider responses, current dates and notification senders must be synthetic and deterministic. Do not send real alerts or require provider credentials for acceptance tests. Inject any runtime secrets securely; do not open `.env` files.

```bash
task install
task doctor
```

Use the [HTTP contract](contracts/scans.md), [worker contract](contracts/worker.md), and [data model](data-model.md) as the expected behavior. Generate the real Alembic revision only during implementation through `task backend:migration -- "area scan coverage"`, then review the generated operations and portable backfill. Never apply experimental migrations to a production database.

## Focused automated verification after implementation

The task backlog adds these suites before implementation behavior:

```bash
task backend:test -- tests/db/test_area_scan_migration.py tests/db/test_scan_coverage.py
task backend:test -- tests/server/routers/test_area_scans.py tests/server/routers/test_recreation_areas.py
task backend:test -- tests/worker/test_area_coverage.py tests/worker/test_area_alerts.py
task frontend:test -- src/frontend/components/AreaCoveragePicker.test.tsx src/frontend/components/ScanForm.test.tsx src/frontend/pages/RecreationArea.test.tsx src/frontend/pages/ScanDetail.test.tsx src/frontend/pages/Dashboard.test.tsx src/frontend/pages/admin/AdminPages.test.tsx
```

Existing campground result/editing, provider import, worker, outbox, notification, admin, and optional-install regressions also run. Expand the focused command list as tests are introduced; the authoritative final gate remains the full Task suites below.

## Acceptance scenarios

| Scenario                            | Fixture and action                                                                                                                            | Expected evidence                                                                                                                                                                     |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| All-area completeness (SC-001)      | One enabled area with 125 eligible synthetic campgrounds, plus disabled/unbookable/unrelated members; save all mode.                          | One saved scan; every eligible member included beyond page one; excluded members absent; provider calls stay campground-level.                                                        |
| Fixed selection (SC-002)            | Four members; select A and C, then catalog adds E and disables C.                                                                             | Only A/C selected; E excluded; C visible as unavailable and not checked; restore C and coverage resumes without adding E.                                                             |
| Membership publication              | Fail Recreation.gov's second dataset parse/import; separately fail enrichment after a valid metadata commit.                                  | Failed/incomplete catalog publishes no membership change; enrichment failure leaves valid committed membership available.                                                             |
| Qualified stays (SC-003)            | A and C both expose site `001`, with separated/expired nights and different electric/type attributes.                                         | Two independent identities; correct links/counts; no cross-site stays; identical alert/detail/dashboard filtering.                                                                    |
| Shared polling (SC-004)             | Ten users with overlapping whole-area/subset/campground scans across the same three campground/date combinations.                             | Three logical checks in a due round, independent matching preferences, no extra calls for UI reads or fresh cooldown observations.                                                    |
| Partial failure and timing (SC-005) | Three successful members and one hung/failing member; fake clock and healthy accepting notifier.                                              | Successful results visible immediately; retained failed results stale; current round bounded; at most one area summary per five-second window; healthy delivery within 60 seconds.    |
| Mutation races (SC-006)             | Concurrent duplicate creates, reordered/repeated selections, edits during a check/window, pause/delete/suspension before send.                | One definition per duplicate identity, atomic conflicts, preserved other subscribers, no stale/excluded alerts, no false all-clear status.                                            |
| Recovery                            | Restart during an attempt, before/after snapshot commit, during summary append/claim/send.                                                    | No orphaned partial snapshot; durable pending intent; expired claims recover; live claims stay exclusive; one logical intent; external acceptance/crash duplication limit documented. |
| Lifecycle/UI (SC-007)               | Keyboard at mobile and desktop widths: area entry, subset search/page selection, failed save, edit/mode/destination changes, partial results. | Choice state retained correctly; unavailable names readable; focus/validation usable; distinct area grouping and correct booking/navigation.                                          |

## Both database paths and installed artifacts

Run populated SQLite fresh/upgrade/backfill/foreign-key, downgrade/re-upgrade and area-data downgrade-refusal tests. Preserve old UUIDs, timestamps, preferences, snapshots and pending campground delivery. Separately run the disposable PostgreSQL migration workflow:

```bash
task backend:migration:test
task backend:packaging:test
```

Migration tests must prove packaged resources work from outside the checkout and compare original campground responses after upgrade. Duplicate legacy definitions must fail preflight without partial schema/data mutation.

## Both runtime paths and browsers

Extend the existing standalone fixture/smoke and distributed admin/worker smoke with synthetic area coverage and notification senders. Standalone must operate without Celery/Valkey/PostgreSQL/Prometheus imports or services; distributed mode must use real locking/dispatch boundaries with stubbed provider and delivery transports.

```bash
task standalone:test
task admin:smoke
task backend:healthcheck:test
task snapshot
task snapshot:check
```

The standalone and distributed smoke harnesses (`tests/server/integration/test_standalone_smoke.py`, `tests/server/integration/test_admin_smoke.py`, `src/frontend/tooling/standalone-live-smoke.ts`, `src/frontend/tooling/admin-live-smoke.ts`) include synthetic area coverage and delivery checks. New area/subset, partial-result, dashboard, and admin area screenshots in `tests/frontend/snapshots/baselines/` (`area-*`, `admin-area-*`, `map-area-*`, `enrichment-area-*`) are visually verified under Chromium; align any platform font baselines if running macOS CI snapshot checks.

## Final implementation gates

```bash
task api:generate
task api:check
task fix
task lint
task check
task test
task docs:check
pre-commit run --all-files
```

Run focused regressions on Python 3.11 as well as default 3.14. Record evidence and update `docs/CHECKLIST.md` only after the relevant implementation work passes. Then run `/speckit-converge`; repeat implementation/convergence until it reports `Converged`. Neither implementation nor convergence is authorized during this planning-only request.

## Rollout boundary

Stop API/worker/beat roles before migration, take a consistent database backup using existing project guidance, apply/verify migrations, and start matching versions together. Area data is not readable by old workers. A downgrade with area data is refused; restoring the pre-upgrade backup is the full rollback path. No production action is part of this guide's creation.

## Verification baseline and local environment limits

- **Tool versions**: Python `3.14.7`, `uv 0.13.1`, Node `v22.23.4`, `pnpm 12.15.0`
- **Verified locally**: `task api:check`, `task docs:check`, `task fix`, `task lint` (`ruff`, `import-linter`, `oxlint`, `oxfmt`), `task check` (`mypy`, `tsc`), `task frontend:test`, `task backend:packaging:test`, `task standalone:test`, `task snapshot:check -- --filter=area-`, and `task test` (`backend:test`, `frontend:test`, `release:test`).
- **Environment limits**: Docker daemon is unavailable in this workspace, so container-backed suites (`task backend:migration:test`, `task admin:smoke`, `task backend:healthcheck:test`, and full CI PostgreSQL/Kind suites) were skipped locally and remain for CI. Binary `cp311` wheels (`mypy`, `psycopg-binary`) are also absent from the offline cache, leaving live Python 3.11 execution to CI alongside static `>=3.11` type/lint checks. Snapshot CI compares baselines on `macos-latest`; Linux renders were inspected for all new/updated area views (`area-*`, `admin-area-*`) without overwriting untouched macOS baselines.
