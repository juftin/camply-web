# Implementation Plan: One Python Package

**Date**: 2026-10-28 | **Status**: Implemented and verified locally
**Worktree branch**: `rebel-parrot` | **Spec**: [spec.md](spec.md)

## Summary and Scope

Replace the four Python workspace distributions with one distribution named
`camply`, containing `camply.server`, `camply.db`, `camply.providers`, and
`camply.worker`. Keep `backend/` as the Python project root, use a `src/`
layout, retain uv and Hatchling, and keep the frontend in `frontend/`.

Base includes providers, persistence, SQLite, and the existing
`populate-database` utility. Four public extras add HTTP serving, distributed
execution, PostgreSQL, and Sentry independently. The long-term default is a
local CLI with SQLite, but implementing the Camply CLI is explicitly outside
this feature. There is no new `camply` command, scan/serve CLI, in-process
scheduler, or bundled frontend in this migration.

## Technical Context

- **Approved Python policy**: Package metadata declares `requires-python = ">=3.11"`.
  Python 3.14 is the standard development, primary CI, Docker, and
  release runtime. Explicit Python 3.11 checks verify minimum compatibility.
- Preserve current dependency constraints when consolidating; use uv to
  reconcile overlapping bounds and regenerate `backend/uv.lock`.
- Use one Hatchling build configuration and one development dependency group.
- Retain pytest/VCR, mypy, Ruff, release tests, Docker builds, OpenAPI checks,
  frontend tests, and existing CI gates.
- No database schema change, provider behavior change, or dependency upgrade is
  planned beyond what is necessary for the approved Python support range.

### Python Runtime and Compatibility

- Set `backend/.python-version` to `3.14`, the shared backend CI action's default
  interpreter to `3.14`, Docker's `PYTHON_VERSION` default to `3.14`, and release
  test fixtures' `UV_PYTHON` to `3.14`. Retain the existing slim-bookworm image
  family rather than adding an operating-system migration.
- Consolidated metadata uses `>=3.11`, Ruff targets `py311`, and mypy checks
  against Python 3.11. A 3.14 development interpreter must not enable
  incompatible syntax or standard-library APIs in the installed package.
- Remove the obsolete pre-3.10 metadata backport requirement through uv and
  use standard-library `importlib.metadata` for distribution metadata.
- Main quality, release, smoke, and deployment checks use 3.14. Add an explicit
  minimum-version job for backend tests and isolated artifact checks on 3.11;
  run the artifact matrix on 3.14 as well. The minimum-version job must override
  interpreter selection explicitly instead of inheriting the 3.14 project pin.
- Refresh the lock for the full supported range; never raise the package floor
  to 3.14 to work around an incompatible dependency. Change existing bounds
  only when necessary to support the approved range, with recorded evidence.
- Update current developer, architecture, agent, and constitution references to
  distinguish the 3.11 support floor from the 3.14 default runtime. Preserve
  historical feature specifications as history.

## Current State and Hazards

See [research.md](research.md) for evidence and alternatives.

1. The virtual root installs all four members. The backend imports sibling
   packages without declaring them, so workspace tests hide packaging defects.
2. `backend.services.operations` imports Celery and Redis at module load.
   Server dependencies cannot exclude these until feature access is guarded.
3. Providers use database models and provider identity data. Persistence stays
   in base; a database-free provider SDK is outside scope.
4. Alembic scripts and Gunicorn configuration currently live outside the
   members' import packages. Runtime resources need explicit distribution rules.
5. Release/version fixtures, Docker, Task, smoke tests, and configuration assume
   workspace members and old import paths.
6. Celery tasks use explicit `camply.*` wire names. Preserve these while
   changing Python task-module paths.

## Target Structure

```text
backend/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── alembic.ini                 # Developer revision-generation configuration
├── config/gunicorn.conf.py     # Existing deployment configuration
├── src/camply/
│   ├── __init__.py             # Lightweight; no application bootstrap
│   ├── __about__.py            # Metadata for distribution "camply"
│   ├── py.typed
│   ├── db/
│   │   ├── migrations/         # Existing graph, env.py, and script.py.mako
│   │   └── ...
│   ├── providers/             # Includes existing cli.py utility
│   ├── server/                # Existing backend HTTP application
│   └── worker/                # Existing tasks and notifications
└── tests/
    ├── db/
    ├── providers/
    ├── server/
    ├── worker/
    └── packaging/
```

| Current imports | New imports          |
| --------------- | -------------------- |
| `backend.*`     | `camply.server.*`    |
| `db.*`          | `camply.db.*`        |
| `providers.*`   | `camply.providers.*` |
| `worker.*`      | `camply.worker.*`    |

Move only what consolidation requires. Keep notifications and scanning tasks
inside `camply.worker`; extracting a shared execution engine is future work.

## Installation and Extras

All installations contain the same modules. Extras add dependencies, not
different wheels, infrastructure, processes, or execution modes.

| Selection     | Dependencies owned here                                                                                                                           | Capability                                                                        |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Base `camply` | Pydantic/settings, HTTPX, SQLAlchemy asyncio, aiosqlite, Alembic, platformdirs, structlog, fake-useragent, Click, Rich                            | Provider/SQLite APIs and existing population utility                              |
| `server`      | FastAPI, Uvicorn, orjson, PyJWT, cryptography, Prometheus client, existing Gunicorn/uvicorn-worker dependencies with appropriate platform markers | Existing API, with distributed operations unavailable unless installed/configured |
| `distributed` | Celery with Redis support, Redis client, Prometheus client                                                                                        | Existing worker/beat using external Valkey/Redis                                  |
| `postgres`    | psycopg binary driver                                                                                                                             | PostgreSQL connections; no database provisioning                                  |
| `sentry`      | sentry-sdk                                                                                                                                        | Existing optional error reporting integrations                                    |

Click/Rich stay in base because provider tooling uses them today. Do not add a
`cli` extra. Keep Prometheus dependencies in both relevant extras rather than
inventing a metrics plugin layer. Preserve conditional Sentry initialization;
a configured DSN without the SDK must produce an installation hint.

Examples of supported dependency combinations:

- Existing full API deployment: `camply[server,distributed,postgres,sentry]`.
- Worker-only deployment: `camply[distributed,postgres,sentry]`, without FastAPI.
- SQLite API without broker integration: `camply[server]`.

Use `[project.optional-dependencies]` for public extras and
`[dependency-groups].dev` for development tools. Change dependencies through
`uv add`, `uv add --optional <extra>`, `uv add --dev`, and `uv remove`, preserving
existing bounds. Keep extras mutually compatible. No `all` extra is needed;
development uses `uv sync --locked --all-extras`.

## Import and Optional-Feature Boundaries

- Root/providers/db imports must work without FastAPI, Uvicorn, Celery, Redis,
  psycopg, or Sentry. Root import must not load every provider, create the ASGI
  application, initialize services, or register worker signals.
- Providers may depend on persistence. Persistence must not import server or
  worker. Server and worker must not import each other's application bootstrap.
- Guard feature-specific Celery/Redis access in
  `camply.server.services.operations`; do not introduce an adapter framework.
- Without distributed dependencies, overview/task-list endpoints use existing
  unavailable/error fields. Provider-sync dispatch uses its existing HTTP 503
  path with a `camply[distributed]` hint. Task detail also returns 503 when the
  capability is absent, rather than incorrectly returning task-not-found.
- Authorization remains in place. Normal API routes/OpenAPI remain usable.
  Preserve response schemas and generated types. Installed dependencies do
  not imply a live broker; retain existing service-outage handling.
- Invoking optional feature entry points without dependencies must give a
  precise installation hint. Catch missing optional imports narrowly; do not
  mask import errors from inside installed packages.

An API-only installation does not execute scheduled campsite checks. Saving
scans remains existing API behavior. Document that workers/beat are still
required; do not advertise a complete standalone scanning server.

### Automated Import Contracts

Use Import Linter as a development dependency, configured in
`backend/pyproject.toml`. An exhaustive layers contract places independent
`server | worker` modules above `providers`, `db`, and shared `__about__`
metadata. Separate forbidden contracts protect base/root imports from optional
third-party dependencies, prevent workers from using server-only dependencies,
and keep the root initializer from bootstrapping component packages.

Server imports of Celery/Redis are forbidden except for two exact existing
edges from the guarded operations service. Unused exceptions are errors.
Sentry imports stay in the two guarded runtime initialization modules. Keep
package markers in services/migration directories so the graph includes them;
regression tests enforce scan coverage and exercise deliberate violations in
temporary source copies. `task backend:imports`, backend lint, the existing CI
lint job, and pre-commit run the same contracts. Retain isolated artifact tests
because static imports cannot prove conditional guards or installed extras.

The layered/forbidden behavior and narrow exceptions follow the tool's
[official contracts documentation](https://import-linter.readthedocs.io/en/stable/contract_types/).

## Compatibility and Resources

- Preserve API URLs, authentication, `CAMPLY_*` settings, provider IDs, database
  tables, revision graph, Celery wire names/queues, and notification payloads.
- Atomically update imports, test monkeypatch strings, subprocesses, Celery
  module lists, Gunicorn/Uvicorn commands, Task, Compose, Docker, OpenAPI
  tooling, smoke fixtures, and pre-commit path exclusions.
- Preserve `populate-database` and its flags; repoint it to
  `camply.providers.cli:populate_database`. Existing admin provisioning and
  OpenAPI module commands move to `camply.server.*`.
- No old top-level import shims are planned: no external compatibility
  obligation has been identified. Document imports as a breaking change and
  use the corresponding release intention.
- Package migrations, `env.py`, and `script.py.mako`. Resolve runtime paths from
  package resources, never the caller's working directory or a source checkout.
  Developer Alembic config targets the same graph; formatting hooks remain
  development-only. Preserve revision IDs/down-revisions; do not squash history.
- Keep Gunicorn configuration in `backend/config/` for deployment. Plain ASGI
  users can launch `camply.server.app:app` with Uvicorn without that file.
- Include the existing license and backend README in standalone sdists.
  Package `py.typed`, and report the single distribution version consistently.
- Container migration startup must not leave subsequent commands running in a
  migration-directory working directory.
- Before deploying, stop beat, drain active tasks, and replace API/worker/beat
  together. Preserve queued JSON task names and arguments. Back up the database;
  rollback changes code/images, not database revision history.

## Delivery Sequence

### 1. Baseline and governance

Capture existing check outcomes, API schema, migration heads, task registry,
entry points, and packaging resources. Verify fresh-SQLite migration behavior
and record current Python incompatibilities separately from the approved
3.11-minimum/3.14-default target.
Amend constitution Principle IV to require internal `camply` subpackages in
place of workspace distributions, retaining frontend/backend separation.
Update its Python policy, version, and sync impact report during implementation.

**Verify**: Baseline evidence and architecture amendment match this design.
The constitution amendment is implemented in version 2.0.0.

### 2. Consolidate distribution and paths

Move code/tests and consolidate metadata, initially retaining the combined
runtime dependency set. Remove workspace configuration/member requirements.
Update executable paths, build layers, version stamping, and release fixtures
in the same integration change so the repository remains runnable. Account
for duplicate test filenames/conftest scope with an explicit pytest layout
and import mode; preserve VCR cassettes and fixtures.

`task dist` clears stale outputs and builds one wheel and one sdist.
`task release:prepare` stamps one backend version plus frontend metadata and
refreshes the lock. Attach both artifacts to GitHub releases. Preserve image
names/tags, CI gates, exact-tag publishing, and major aliases. No PyPI uploads.

**Verify**: Existing backend/release tests, OpenAPI drift, Docker build, and
resource checks pass against the new package structure.

### 3. Isolate optional dependencies

Move dependencies into four extras and guard optional imports/operations.
Change development and Docker extra selection in the same integration change
that partitions dependencies, so normal workflows remain usable. Development
tasks install all extras; production Docker selects
`server`, `distributed`, `postgres`, and `sentry` without dev tools. Ensure
subsequent `uv run` calls preserve the selected extras rather than pruning
them. Full installations retain existing behavior.

**Verify**: Base, server-only, worker-only, PostgreSQL, and Sentry checks run in
separate environments on 3.14 and verify compatibility on 3.11. All-extras tests
alone cannot prove isolation.

### 4. Verify artifacts and update documentation

Add Task-backed packaging checks to CI and `task test`. Build a wheel from the
sdist and install both wheel paths outside the checkout, without dev packages,
editable installs, or inherited source paths. Exercise resources, existing
entry points, version metadata, server imports, and task registration.
Update current architecture/setup/release docs and complete required checks.
Keep the artifact matrix in its dedicated task; normal `backend:test` excludes
that directory so root testing and CI do not run the matrix twice.

**Verify**: [Installation contract](contracts/installation.md) and
[validation guide](quickstart.md) pass. Release fixtures produce exactly one
matching wheel/sdist pair without generic sibling distributions.
Track requirement coverage and final evidence in the
[readiness checklist](checklists/requirements.md) and
[acceptance evidence](quickstart.md#acceptance-evidence), respectively.

## Constitution Check

| Principle           | Design outcome                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------- |
| Reliability         | Provider/scanning behavior, task names, and notification semantics retained.             |
| Type safety         | Consolidated Ruff/mypy; guarded optional imports remain typed.                           |
| Modern workflow     | uv/Task retained; new verification has Task entrypoints.                                 |
| Monorepo boundaries | Frontend/backend separation retained; internal subpackages replace workspace boundaries. |
| Verification        | Existing suites retained; isolated artifact and optional-feature checks added.           |

**Gate resolved**: Constitution version 2.0.0 now requires internal `camply`
subpackages and the approved Python support policy. This implements the user's
authorized architecture change. Post-implementation review found no additional
architecture exceptions.

## Deferred Work

- Implementing the Camply CLI, including scan/serve commands or legacy flags.
- Extracting scanning/notification logic for shared local execution.
- In-process scheduling, concurrency control, shutdown/restart behavior, and
  duplicate-scheduler prevention under reload/multiple ASGI workers.
- Bundling React assets into Python artifacts and serving the SPA.
- New providers, database redesign, and dependency upgrades unrelated to the
  approved Python support range.
- PyPI publication. Verify ownership of the intended `camply` project and its
  relationship to legacy releases before separately enabling publication.

This migration prepares package boundaries without delivering those features.
