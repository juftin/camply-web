# Research: One Python Package

## Repository Audit

| Evidence                                                                             | Consequence                                                                                 |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `backend/pyproject.toml` aggregates four workspace members.                          | Replace the virtual aggregator with one installable project and lockfile.                   |
| Member builds use Hatchling; backend imports undeclared sibling packages.            | Retain Hatchling and test installed artifacts independently of the development environment. |
| Provider base/registry import database models and identity data.                     | Keep SQLAlchemy, settings, and SQLite in base; no database-free SDK extraction.             |
| Provider CLI/ingestion use Click and Rich.                                           | Preserve base dependencies and the existing utility; do not implement a new CLI.            |
| `backend/services/operations.py` imports Celery/Redis at module load.                | Guard feature access so server-only imports work.                                           |
| Operations schemas represent unavailable/error states; sync dispatch has a 503 path. | Reuse current response shapes and errors rather than change the API schema.                 |
| `worker/celery_app.py` lists Python module paths; tasks declare explicit wire names. | Rename Python paths, preserve wire names and JSON payloads.                                 |
| Worker scanning uses Valkey locks and queues notifications.                          | Consolidation does not create a single-process scanning runtime.                            |
| SQLite defaults and dialect-specific search/migration behavior already exist.        | Keep SQLite defaults and verify migrations; only the PostgreSQL driver becomes optional.    |
| Alembic scripts and Gunicorn configuration sit outside import packages.              | Package migrations; retain Gunicorn config with deployment tooling.                         |
| Task, release fixtures, Docker, and CI assume four distributions.                    | Update stamping, artifacts, fixtures, dependency selection, and commands together.          |
| Constitution Principle IV mandates workspace packages.                               | Amend during implementation to reflect the requested internal-subpackage design.            |

Unless rooted otherwise, paths above refer to existing
`backend/packages/<member>/` directories. This audit reads configuration/source;
it does not claim existing runtime checks have been executed.

## Decisions and Alternatives

### One distribution with existing subpackages

**Decision**: `backend/src/camply/{server,db,providers,worker}`.

**Rationale**: Components already release together. Preserve internal boundaries
without distribution coordination; `server` identifies the HTTP component.

**Alternatives**: Retaining the workspace conflicts with the selected direction.
A repository-root Python project needlessly changes frontend/backend boundaries.
New scanning/notification abstractions add unrelated runtime work.

### Base plus four extras

**Decision**: Base contains providers/SQLite and existing tooling; `server`,
`distributed`, `postgres`, and `sentry` add dependencies.

**Rationale**: The user selected a future local CLI/SQLite default and explicitly
excluded CLI implementation. No separate CLI extra or new CLI is promised.

**Alternatives**: Optional persistence requires untangling existing providers.
An `all` extra duplicates a combination; development can use `--all-extras`.

Use published optional dependencies for extras and a local group for dev tools.
[uv dependency documentation](https://docs.astral.sh/uv/concepts/projects/dependencies/)

### Verify installed artifacts

**Decision**: Exercise a direct wheel and an sdist-rebuilt wheel outside the
checkout without dev dependencies.

**Rationale**: Editable/all-extras tests hide dependency leaks and missing data.

**Alternatives**: Build success alone does not prove runtime usability. Retain
application suites and add focused packaging checks rather than duplicate every
test across every extra combination.

Validate builds without development source overrides when preparing releases.
[uv packaging guide](https://docs.astral.sh/uv/guides/package/)

### Python support and runtime defaults

**Decision**: Declare `requires-python = ">=3.11"`; use Python 3.14 for local
development, primary CI, Docker, and release tooling. Run explicit 3.11
compatibility tests in addition to 3.14 verification.

**Rationale**: The user explicitly selected this policy. Existing provider DTOs
import `enum.StrEnum`, and database search imports `typing.Self`, so the old
3.9 metadata does not reflect the current implementation. Keep the minimum
syntax/API target at 3.11 while defaulting operational tooling to 3.14.

**Alternatives**: Keeping 3.9 would require unrelated backport work. Requiring
3.14 would exclude supported 3.11 consumers. Testing only 3.14 would leave the
declared minimum unverified.

The official image repository provides the 3.14 slim-bookworm variant, allowing
the Python runtime update without changing the Debian family.
[Official Python image](https://github.com/docker-library/python/blob/master/3.14/slim-bookworm/Dockerfile)

**Implementation ordering**: Partitioning dependencies into extras and updating
development/CI/Docker extra selection occur together in T013. Deferring
selection until T023 could break normal workflows between those steps.

### Preserve execution behavior

**Decision**: Retain distributed scanning and API-only limitations.

**Rationale**: Extras choose dependencies; local scheduling needs separate
lifecycle/concurrency/notification work. A new CLI is an explicit non-goal.

**Alternatives**: Embedded Celery or a new local launcher would expand this
migration and obscure the distinction between packaging and execution.

## Baseline and Implementation Evidence — 2026-10-28

- A temporary snapshot of the tracked backend, excluding environment files,
  passed the original suite on Python 3.14 and 3.11: **569 passed, 12 skipped**
  on each interpreter. The only warning was the existing Starlette/HTTPX
  deprecation. Fresh SQLite upgraded through all 15 existing revisions to
  `09367969f1a4`; the original configuration required the workspace DB directory
  as its working directory.
- The pre-migration API schema and five explicit `camply.*` Celery task names
  were captured before relocation. After migration, API paths/components and
  all task names match. The OpenAPI information title intentionally follows
  the consolidated application name, `camply`; version remains `0.1.0`.
- The migrated backend suite passes on both supported verification versions:
  **579 passed, 12 skipped** on Python 3.14 and 3.11. Added tests exercise
  migration resources, optional operations, drivers, and configured reporting.
- Both isolated artifact matrices pass: **22 tests on 3.14** and **22 on 3.11**.
  They cover direct and standalone-sdist-rebuilt wheels across base, server,
  distributed, postgres, server+sentry, and distributed+sentry installations.
- The desired release-policy regression failed against the original 3.12
  defaults before tooling changes. Artifact tests also caught a namespace
  rewrite affecting SQL foreign-key strings; those strings were restored to
  preserve the schema. Final migration, application, and artifact checks pass.
- Runtime dependency versions were preserved during lockfile consolidation;
  obsolete workspace packages/backport requirements were removed. No unrelated
  third-party version upgrades remain.
- See [validation outcomes](quickstart.md#execution-results) for release,
  Docker, live-service, quality, frontend, and pre-commit verification.

## Follow-up: Import Linter Enforcement

The user requested [Import Linter](https://github.com/seddonym/import-linter)
to preserve dependency separation. Its development-only dependency and six
contracts now live in `backend/pyproject.toml`; the existing lint CI job and
local pre-commit hook run them through `task backend:imports`.

Exhaustive layers enforce independent server/worker components above providers,
database, and metadata. Forbidden contracts protect optional dependencies,
guarded broker/Sentry gateways, and root imports, including indirect paths.
Only the four existing guarded gateway edges are ignored; stale exceptions
fail. Installed-extra tests remain necessary to prove the guards' runtime
behavior and dependency closure.

Initial graph inspection revealed omitted namespace directories: server
services and packaged migrations/versions lacked `__init__.py` markers. Adding
markers includes all source directories without changing migration identities.
Tests now reject future directories missing markers and deliberate import
violations in those directories. The baseline contract test failed before
configuration was added; final checks accept the real source and reject the
mutated source copies without editing or importing the live application.
