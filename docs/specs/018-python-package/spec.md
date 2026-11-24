# Feature Specification: One Python Package

**Created**: 2026-10-28 | **Status**: Implemented and verified locally

## Scope

Consolidate the backend workspace into one distributable Python package with
optional extras. The long-term product supports a local CLI and a standalone
web server; this feature prepares packaging for those uses. Implementing the
Camply CLI or a standalone scheduling runtime is explicitly outside scope.

## User Scenarios and Testing

### US1: Install providers and persistence (P1)

A consumer installs `camply` and imports providers/SQLite persistence without
HTTP-server, task-queue, PostgreSQL, or Sentry dependencies.

**Independent test**: Install a wheel outside the checkout, import base APIs,
resolve migrations, and run existing `populate-database --help` without network.

**Acceptance**:

1. Root/providers/db imports work without optional dependencies or application
   bootstrap side effects.
2. Provider IDs, SQLite defaults, and population-tool flags remain unchanged.
   No new `camply` console command is introduced.
3. Installed wheels include migration scripts/templates and typing metadata;
   use does not depend on repository-relative paths.

### US2: Select runtime dependencies independently (P1)

An operator installs API or worker dependencies separately, or combines extras
for the existing distributed deployment.

**Independent test**: Exercise `server` without Celery/Redis and `distributed`
without FastAPI/Uvicorn; verify the combined installation preserves behavior.

**Acceptance**:

1. Server-only can import the app, generate OpenAPI, and serve SQLite-backed
   routes without a broker connection at startup.
2. Without distributed dependencies, operations reads report unavailable using
   existing fields. Task detail and dispatch return actionable HTTP 503;
   authorization stays enforced.
3. Worker-only registers existing tasks and uses configured external services
   without server dependencies. PostgreSQL and Sentry are independently opt-in.
4. Missing optional capabilities produce precise installation hints when used;
   unrelated base imports remain usable.
5. Server-only does not claim to execute scheduled scans without workers/beat.

### US3: Build and release one distribution (P2)

A maintainer develops/builds/releases one Python project with one version and
one wheel/sdist pair.

**Independent test**: Release fixtures stamp a synthetic version, build both
artifacts, rebuild a wheel from the sdist, and verify installation and assets
without publishing.

**Acceptance**:

1. Task, CI, Docker, Compose, and OpenAPI tooling use the final layout.
2. Installed runtime metadata reports one version; releases attach both
   artifacts instead of four workspace source distributions.
3. API contracts, authentication, database history, provider IDs, Celery wire
   names/payloads, and notification behavior remain compatible.
4. Package metadata requires Python `>=3.11`. Development, primary CI, Docker,
   and release tooling default to Python 3.14; explicit Python 3.11
   compatibility checks verify the supported minimum.

## Requirements

- **FR-001**: One `backend/pyproject.toml`, lockfile, build configuration, and
  `camply` distribution replace workspace members.
- **FR-002**: Existing components become `camply.server`, `camply.db`,
  `camply.providers`, and `camply.worker`, with explicit internal boundaries.
- **FR-003**: Base owns providers/persistence/SQLite; public extras are `server`,
  `distributed`, `postgres`, and `sentry`. Dev tools stay in a development group.
- **FR-004**: Preserve the existing population utility without implementing the
  Camply CLI, scan/serve commands, or legacy flag compatibility.
- **FR-005**: Optional dependencies must not leak into base imports; server and
  worker installations remain independent within documented capabilities.
- **FR-006**: Package migrations/templates, typing marker, license, and metadata
  so artifacts work independently of the source checkout.
- **FR-007**: Preserve database revision identities, provider identities, API
  schemas, configuration names, Celery wire names, and notification semantics.
- **FR-008**: Update development, release, deployment, governance, and tests.
- **FR-009**: Verify artifact installation in isolated environments without dev
  dependencies; editable/all-extras tests are insufficient.
- **FR-010**: Do not publish to PyPI, bundle the frontend, or implement
  in-process scheduling as part of this migration.
- **FR-011**: Declare Python `>=3.11`, standardize development/primary CI/Docker/
  release defaults on Python 3.14, and verify minimum-version compatibility on
  Python 3.11. Tooling must retain the 3.11 syntax/API floor.
- **FR-012**: Enforce internal dependency layers and optional-runtime import
  boundaries with Import Linter in lint/CI/pre-commit. Keep exact guarded
  broker exceptions narrow, fail stale exceptions, and verify forbidden
  imports with regression tests, including source-directory scan coverage.

## Success Criteria

- **SC-001**: Exactly one matching wheel/sdist pair replaces four backend source artifacts.
- **SC-002**: Base imports/population help pass with optional runtime packages absent.
- **SC-003**: Server-only and worker-only artifact tests pass with opposing dependencies absent.
- **SC-004**: Direct and sdist-rebuilt wheels contain usable migration resources;
  database upgrades retain revision history.
- **SC-005**: Existing quality, API, release, and deployment checks pass after relocation.
- **SC-006**: Installed metadata declares `>=3.11`; runtime defaults and release
  fixtures consistently select 3.14; backend tests and isolated artifact checks
  pass on both 3.11 and 3.14.
- **SC-007**: Import Linter accepts the current source and rejects deliberate
  upward, cross-runtime, optional-dependency, root-bootstrap, and unclassified
  module violations. All Python source directories remain in its scan.

## Assumptions and Edge Cases

- Intended distribution/import name is `camply`; PyPI ownership and legacy
  release compatibility must be verified before future publication.
- No external compatibility obligation for old top-level imports has been
  identified. Document the import migration as breaking.
- Extras are additive; installing dependencies does not provision/start services.
- Missing dependencies differ from configured services being unavailable.
- Duplicate test filenames, monkeypatch strings, historical revision imports,
  package data, and Celery autodiscovery need explicit verification.
- Base supports the future local CLI direction; that CLI does not exist yet.
- Python 3.11 is a compatibility target, not the default runtime. New syntax or
  standard-library usage must work there despite development running on 3.14.
