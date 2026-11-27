# Validation Guide

These scenarios verify the implemented migration. `backend:packaging:test`
builds and checks installed artifacts. No Camply CLI or local scheduler is
delivered.

## Development and Build

```bash
task install
task backend:lint
task backend:imports
task backend:check
task backend:test
task api:check
task release:test
task dist
```

Backend development sync installs all extras/dev tools from the lockfile.
The project pin, main CI, container default, and release fixtures use Python
3.14. Metadata declares `>=3.11`; Ruff/mypy retain the 3.11 compatibility floor.
Expected output: one wheel and one sdist. Release fixtures verify stamping,
asset selection, and rebuilding the sdist into a wheel.

## Isolated Installation Matrix

```bash
task backend:packaging:test PACKAGING_PYTHON=3.14
task backend:packaging:test PACKAGING_PYTHON=3.11
```

The task installs artifacts with uv in temporary environments, then runs
checks outside the checkout. No dev dependencies, editable installs,
or inherited `PYTHONPATH`/source paths are allowed in these environments.
Explicit interpreter selection must override the 3.14 project pin. Run the
matrix below on both versions; primary CI additionally runs the full normal
checks on 3.14, and the compatibility job runs backend tests on 3.11.

1. **Base**: Assert optional runtimes absent; import root/providers/db; run
   `populate-database --help`; locate migrations; upgrade a fresh temporary
   SQLite database and a synthetic earlier-revision database.
2. **Server only**: Assert Celery/Redis/psycopg/Sentry absent; generate OpenAPI;
   start Uvicorn against `camply.server.app:app`; check health and a SQLite
   route. Authorized operations reads report unavailable; dispatch/task detail
   return 503 without worker bootstrap or broker connections.
3. **Distributed only**: Assert FastAPI/Uvicorn/Gunicorn/psycopg/Sentry absent;
   import Celery app and compare registered names with the baseline. Import
   checks must not connect to a broker.
4. **PostgreSQL/Sentry**: Check base-plus-postgres driver selection and retain
   real PostgreSQL migration smoke checks. Check server-plus-sentry and
   distributed-plus-sentry initialization with synthetic settings and mocked
   transport; never contact live Sentry or provider services.
5. **Combined**: Check metadata/dependency consistency; use normal application
   suites and Docker checks for full-stack behavior rather than duplicate all
   application tests in packaging environments.
6. Repeat critical base/resource/import checks using the sdist-rebuilt wheel.

## Deployment and Final Checks

```bash
task fix
task lint
task check
task test
task api:check
task backend:build
task search:smoke
task maps:verify
task admin:smoke
task pre-commit
```

Use existing CI infrastructure for Docker/browser checks. Record unavailable
infrastructure explicitly; never mark unexecuted checks passed. Preserve the
existing snapshot CI gates; packaging alone needs no new UI snapshots.

Verify Compose commands, container migrations, provider dispatch, and installed
metadata agree on new paths. Stop beat, drain active tasks, and replace the
API/worker/beat deployment together. Queued JSON jobs keep existing wire names.

## Acceptance Evidence

These implementation checks record validation evidence. They are kept outside
`checklists/` because Spec-Kit treats unchecked items there as blockers to
starting implementation. Design readiness is tracked separately in the
[requirements checklist](checklists/requirements.md).

- [x] SC-001: Release fixtures produce exactly one matching wheel/sdist pair (T009, T024, T027).
- [x] SC-002: Base imports and existing utility help work without optional runtimes (T012, T016, T017).
- [x] SC-003: API-only/worker-only installations work without opposing dependencies (T018–T023).
- [x] SC-004: Direct/rebuilt wheels contain migrations and preserve database history (T010, T012, T015, T024).
- [x] SC-005: Existing quality/API/release/deployment checks pass after relocation (T011, T027, T028, T031).
- [x] SC-006: Metadata requires `>=3.11`, defaults use 3.14, and backend/artifact checks pass on both versions (T006, T008, T009, T023–T026).
- [x] SC-007: Import Linter contracts pass and architecture regressions reject forbidden imports and unscanned directories (T032–T034).

Record actual outcomes and infrastructure limits alongside these checks. Mark
them complete only when their corresponding validation has run successfully.

## Execution Results

Verified locally on 2026-10-28:

| Check                                 | Result                                                                                                                                                     |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend suite, Python 3.14            | 579 passed, 12 skipped                                                                                                                                     |
| Backend suite, Python 3.11            | 579 passed, 12 skipped                                                                                                                                     |
| Isolated artifacts, Python 3.14       | 22 passed; direct and sdist-rebuilt wheels                                                                                                                 |
| Isolated artifacts, Python 3.11       | 22 passed; direct and sdist-rebuilt wheels                                                                                                                 |
| Release regressions                   | 10 passed, including standalone sdist rebuilding and publication selection                                                                                 |
| `task fix`, `task lint`, `task check` | Passed across backend and frontend                                                                                                                         |
| `mise exec node@24 -- task test`      | Passed: release, backend, artifact matrix, and 336 frontend tests                                                                                          |
| `task api:check`                      | Passed; generated TypeScript client unchanged                                                                                                              |
| PostgreSQL search smoke               | 9 passed                                                                                                                                                   |
| Maps verification                     | PostgreSQL and Chromium/API checks passed                                                                                                                  |
| Admin smoke                           | Live browser/API/Celery/monitoring check passed                                                                                                            |
| Docker build and runtime smoke        | Passed with Python 3.14, no dev dependencies, non-root migration startup, `/app` working directory, API health, task registry/beat, and in-memory dispatch |
| GitHub Actions validation             | actionlint and ShellCheck passed for CI/release/publish workflows                                                                                          |
| Changed/new-file pre-commit hooks     | Passed for all migration files, including relocated Python/tests                                                                                           |

The 12 normally skipped backend tests are opt-in live-service tests, verified
separately with the PostgreSQL/map/admin smoke tasks above. Newly added artifact
checks and live smoke tests use synthetic settings/data and test-owned
resources; existing provider VCR recordings are preserved. No PyPI/GHCR
publication, external messaging, or operator database migration was performed.

An initial frontend run under the host's Node 26 failed an authentication
navigation test; the unchanged frontend passes all **336 tests** under its
configured Node 24 runtime. Use `mise exec node@24 -- task test` when the host's
default Node differs from `frontend/.node-version`.

Repository-wide `task pre-commit -- --all-files` encounters a pre-existing
configuration issue: `check-yaml` expects one YAML document, whereas the
unchanged pnpm 12 lockfile contains multiple documents. The migration leaves
that unrelated lockfile/hook policy unchanged. Hooks pass when run against all
changed/new migration files. Narrow existing docstring-hook exclusions were
extended for new valid attribute docstrings; AST and Ruff checks still cover
those files.

### Import Linter Follow-up

- Six contracts pass through `task backend:imports` and backend lint, including
  lint invocations targeting a subset of Python files.
- The architecture suite has 21 passing cases on Python 3.14 and 3.11. It
  checks accepted source, deliberate violations, source-directory coverage,
  and rejection of stale gateway exceptions.
- The full Python 3.14 backend suite now passes **600 tests**, with the same
  12 opt-in integration skips. Ruff and mypy pass for all 104 source modules.
- Both 22-case installed-artifact matrices pass after adding package markers;
  base installations also verify that Import Linter/Grimp are absent.
- The 10 release regressions pass. Application logic, API/task contracts,
  provider behavior, and revision identities remain unchanged.
