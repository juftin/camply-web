# Tasks: One Python Package

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[compatibility invariants](data-model.md), and
[installation contract](contracts/installation.md).

Implementation and verification are complete. All tasks below have recorded
evidence in [quickstart.md](quickstart.md#execution-results) and
[research.md](research.md#baseline-and-implementation-evidence--2026-10-28).
Tests cover packaging/optional-feature regressions in addition to the existing
application suites. No task implements a Camply CLI or local scheduler.

## Phase 1: Baseline and Governance

- [x] T001 Record baseline check outcomes on Python 3.11/3.14, SQLite migration behavior, API schema, task names, and existing entry points in `specs/012-python-package/research.md`; distinguish existing failures from migration regressions and the approved runtime-policy update.
- [x] T002 Amend Principle IV in `.specify/memory/constitution.md` to require internal `camply` subpackages instead of workspace distributions; retain frontend/backend boundaries, document the Python 3.11 floor and 3.14 default, bump the constitution version, and update its sync impact report.

## Phase 2: Consolidation Foundation

Keep T003–T011 in the same integration change: relocation and executable paths
must agree before the repository is considered runnable. Initially retain the
combined runtime dependencies so optional-feature work is a distinct step.

- [x] T003 Update desired layout/version/artifact assertions in `tests/release.test.mjs` before relocation and establish their expected failures; scaffold the shared isolated artifact harness in `backend/tests/packaging/conftest.py` for later base/extra tests.
- [x] T004 Move source from `backend/packages/{backend,db,providers,worker}` to `backend/src/camply/{server,db,providers,worker}` and tests/fixtures/cassettes to `backend/tests/{server,db,providers,worker}`; preserve file contents except required imports/paths.
- [x] T005 Update absolute imports, monkeypatch targets, dynamic module strings, subprocess commands, and Celery module lists throughout `backend/src/camply/` and `backend/tests/`; preserve explicit task names and payloads.
- [x] T006 Convert `backend/pyproject.toml` into the sole Hatchling project named `camply` with `requires-python = ">=3.11"`, Ruff `py311`, and mypy Python 3.11; set `backend/.python-version` to 3.14, consolidate metadata/dependencies/dev tools, remove workspace configuration and the obsolete metadata backport through uv, add `py.typed`, configure pytest discovery/import mode, and regenerate `backend/uv.lock`.
- [x] T007 Update `backend/Taskfile.yaml` and root `Taskfile.yaml` source/test/config paths, provisioning/OpenAPI commands, migration commands, and synchronization for a single project; keep existing task names.
- [x] T008 Update `backend/Dockerfile`, `backend/entrypoint.sh`, `backend/docker-compose.yaml`, `.github/actions/setup-backend/action.yaml`, `.github/workflows/ci.yaml`, and path-dependent smoke/browser fixtures for the relocated project; set Docker and primary CI defaults to Python 3.14 while retaining the slim-bookworm image family and existing deployment/CI behavior.
- [x] T009 Update root `Taskfile.yaml`, `.releaserc.json`, and `tests/release.test.mjs` so release preparation stamps one backend version plus frontend metadata and builds/attaches one wheel and one sdist; set fixture interpreter defaults to 3.14, retain image publication semantics, and omit PyPI publishing.
- [x] T010 Relocate migration resources under `backend/src/camply/db/migrations/`, move developer Alembic/Gunicorn configuration to `backend/alembic.ini` and `backend/config/gunicorn.conf.py`, and include `backend/LICENSE` plus required package data in `backend/pyproject.toml`; retain the entire revision graph.
- [x] T011 Validate the consolidated full-dependency layout with existing backend, release, OpenAPI, and Docker checks; record results in `specs/012-python-package/quickstart.md` and fix relocation regressions before extras work.

## Phase 3: US1 — Base Providers and Persistence (P1)

**Goal**: Install provider/SQLite functionality independently of optional runtimes.
**Independent check**: Base wheel installation outside the checkout, including
imports, population help, migration resources, and SQLite upgrades.

- [x] T012 [US1] Add failing isolated base-install/resource/entry-point tests in `backend/tests/packaging/test_base_install.py`; assert optional packages are absent and exercise both direct and sdist-rebuilt wheels without dev dependencies.
- [x] T013 [US1] Partition dependencies in `backend/pyproject.toml` into base plus `server`, `distributed`, `postgres`, and `sentry` using uv commands, preserve compatible bounds, and regenerate `backend/uv.lock`; retain Click/Rich and simultaneously update `backend/Taskfile.yaml`, `.github/actions/setup-backend/action.yaml`, and `backend/Dockerfile` to select all extras for development or explicit production extras without dev tools.
- [x] T014 [US1] Make `backend/src/camply/__init__.py` lightweight and centralize distribution metadata using stdlib `importlib.metadata` in `backend/src/camply/__about__.py`; update server metadata consumers and verify no server/worker initialization occurs on base imports.
- [x] T015 [US1] Provide installed-resource Alembic configuration in `backend/src/camply/db/migration.py` and `backend/alembic.ini`; keep formatter hooks developer-only, and verify fresh/earlier-revision synthetic SQLite upgrades without source-relative paths.
- [x] T016 [US1] Preserve `populate-database` in `backend/pyproject.toml` pointing to `backend/src/camply/providers/cli.py`; keep existing flags and ensure imports/help work offline without optional runtimes or a new `camply` script.
- [x] T017 [US1] Run isolated base checks and relocated provider/database suites in `backend/tests/`; record resource, dependency-absence, and database-history results in `specs/012-python-package/quickstart.md`.

## Phase 4: US2 — Independent Runtime Extras (P1)

**Goal**: API and worker extras import/run independently within documented scope.
**Independent check**: Server-only without Celery/Redis, distributed-only without
FastAPI/Uvicorn, and focused PostgreSQL/Sentry combinations.

- [x] T018 [US2] Add failing server/worker/missing-extra checks in `backend/tests/packaging/test_runtime_extras.py` and operations regressions in `backend/tests/server/`; verify auth, unavailable fields, HTTP 503, broker-free startup, and unchanged task names.
- [x] T019 [US2] Guard Celery/Redis feature imports in `backend/src/camply/server/services/operations.py` and retain authorized error handling in `backend/src/camply/server/routers/admin.py`; preserve response schemas and distinguish missing dependencies from service outages.
- [x] T020 [US2] Keep Sentry imports conditional in `backend/src/camply/server/app.py` and `backend/src/camply/worker/celery_app.py`; provide missing-SDK hints only when configured, and test initialization with synthetic settings/mocked transport.
- [x] T021 [US2] Keep SQLite imports usable without psycopg in `backend/src/camply/db/config.py`; provide a precise `postgres` installation hint when the configured PostgreSQL driver is absent and preserve real connection errors.
- [x] T022 [US2] Verify import boundaries and optional-entry-point failures in `backend/tests/packaging/test_runtime_extras.py`; root/providers/db must not bootstrap applications, and server/worker must not import each other's bootstrap or signals.
- [x] T023 [US2] Verify extra selection in `backend/Taskfile.yaml`, `.github/actions/setup-backend/action.yaml`, and `backend/Dockerfile` survives subsequent commands; run the isolated extra matrix and backend suites on Python 3.14 and 3.11, retaining the selection established with T013.

## Phase 5: US3 — Artifact and Release Verification (P2)

**Goal**: A single version-stamped distribution works outside the repository.
**Independent check**: One wheel/sdist pair; standalone sdist rebuild; isolated
installs; release fixture and Docker command validation without publication.

- [x] T024 [US3] Extend `tests/release.test.mjs` to verify the single version, `Requires-Python: >=3.11`, 3.14 runtime defaults, wheel/sdist filenames, license/typing/migration data, accurate extra metadata, stale-output cleanup, and rebuilding the sdist without sibling repository directories.
- [x] T025 [US3] Complete shared artifact-harness coverage in `backend/tests/packaging/conftest.py` with uv-created temporary environments, explicit 3.14/default or 3.11/compatibility interpreter selection, and cleared source paths; add `backend:packaging:test` with `PACKAGING_PYTHON` selection in `backend/Taskfile.yaml`, exclude packaging tests from normal `backend:test`, and include the dedicated task once in root `Taskfile.yaml` testing without recursive invocations.
- [x] T026 [US3] Add the isolated artifact matrix and backend-suite compatibility job to `.github/workflows/ci.yaml`; primary jobs use Python 3.14, the minimum-version job explicitly overrides interpreter selection to 3.11, and existing frontend/API/smoke/snapshot checks remain intact with explicit extra selection.
- [x] T027 [US3] Validate version stamping, asset selection, and exact-tag publication plans with `tests/release.test.mjs`; preserve GHCR aliases/events and verify no PyPI upload is enabled in `.releaserc.json` or workflows.
- [x] T028 [US3] Build and smoke-check `backend/Dockerfile`, `backend/entrypoint.sh`, and `backend/docker-compose.yaml` for migrations, API startup, worker registration, beat task names, and provider-sync dispatch using synthetic data and existing integration infrastructure.

## Phase 6: Documentation and Final Verification

- [x] T029 Update current layout/extras/install/release instructions in `README.md`, `backend/README.md`, `docs/agents/DEVELOPER_GUIDE.md`, `docs/agents/RELEASES.md`, and `docs/agents/CONFIGURATION.md`; distinguish Python 3.11 support from 3.14 runtime defaults, and document API-only scheduling limitations and breaking import paths.
- [x] T030 Update `AGENTS.md`, `docs/agents/PLAN.md`, affected `docs/agents/DESIGN_*.md`, `.pre-commit-config.yaml`, and `docs/agents/CHECKLIST.md` for the final architecture; retain historical specs as history and document deployment drain/restart/rollback steps.
- [x] T031 Run the complete validation sequence from `specs/012-python-package/quickstart.md`, reconcile spec/plan/task coverage with `specs/012-python-package/checklists/requirements.md`, record actual outcomes/remaining infrastructure limits, and mark tasks/acceptance checks complete only with evidence.

## Phase 7: Import Architecture Enforcement

- [x] T032 Add Import Linter to development dependencies and define exhaustive internal layers plus base/runtime/root import restrictions in `backend/pyproject.toml`; include service/migration directories in graph coverage with package markers and preserve exact guarded broker exceptions.
- [x] T033 Integrate `backend:imports` into `backend/Taskfile.yaml` lint and `.pre-commit-config.yaml`, ignore graph caches, and document the contracts in `backend/README.md` and `docs/agents/DEVELOPER_GUIDE.md`.
- [x] T034 Add behavioral violation/scan-coverage regressions in `backend/tests/test_import_boundaries.py`, verify development tools stay out of installed artifacts, and record Python 3.11/3.14 checks in `specs/012-python-package/quickstart.md`.

## Dependencies and Execution Order

```text
T001 → T002 → consolidation foundation (T003–T011)
                      ↓
             US1 base (T012–T017)
                      ↓
             US2 extras (T018–T023)
                      ↓
             US3 artifacts/CI (T024–T028)
                      ↓
             documentation/checks (T029–T031)
```

Write behavioral regressions before optional-import changes. US2 depends on
US1's package/dependency definitions; US3's final matrix depends on both.
T013 includes development/CI/Docker extra selection in the same change as the
dependency partition; T023 verifies it rather than deferring those updates.
T003 supplies common harness scaffolding for T012/T018; T025 completes coverage
and Task integration rather than creating a second test runner.
Release path changes in T009 are foundational; T024/T027 strengthen verification
after extras are final. T010 establishes resources; T015 makes wheel access
independent of repository/developer configuration.

Potential independent work after relocation: US1 population-help and SQLite
fixtures; US2 server operations and driver/Sentry regressions; US3 release
artifact assertions and container smoke checks. These opportunities do not
require parallel agents or separate changes touching shared metadata.

## Delivery Strategy

Use one feature branch with reviewable commits: baseline/governance,
distribution/path consolidation, optional-dependency isolation, then artifact
verification/documentation. Do not ship a partially relocated project or mark
the migration complete before the isolated installations pass. Future CLI,
shared scanning engine, embedded scheduler, UI bundling, and PyPI publication
remain separate features.
