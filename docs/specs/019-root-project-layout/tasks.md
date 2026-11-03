# Tasks: Root Project Layout

**Input**: [Specification](spec.md), [plan](plan.md), research, model, and contracts in this directory.

## Phase 1: Setup

- [x] T001 Verify baseline, checklist gates, and deployment inventory using `docs/specs/013-root-project-layout/checklists/requirements.md` and `docker-compose.yaml`.
- [x] T002 Amend directory governance in `.specify/memory/constitution.md` and align `.specify/templates/*.md` with root projects.

## Phase 2: Foundation

- [x] T003 Capture failing root-layout/artifact regressions in `tests/packaging/` before completing source moves.
- [x] T004 Establish root task orchestration in `Taskfile.yaml` with included `taskfiles/python.yaml` and `taskfiles/frontend.yaml`.

## Phase 3: US1 — Complete distributions (P1)

**Independent test**: Standard root build and direct wheel both contain the UI; an unmodified sdist rebuilt outside the checkout without JavaScript retains its assets.

- [x] T005 [US1] Move `backend/pyproject.toml`, `backend/uv.lock`, `.python-version`, and Python source/resources into root metadata and `src/camply/`.
- [x] T006 [US1] Add the development build frontend using uv in `pyproject.toml` and `uv.lock`.
- [x] T007 [US1] Implement standard-build-only compilation, frozen install, archive inventory, and forced inclusion in `hatch_build.py`.
- [x] T008 [US1] Package existing Gunicorn configuration in `src/camply/server/gunicorn.py`.
- [x] T009 [US1] Extend `tests/packaging/` for default/direct/archive builds, invalid/stale assets, missing tools, installed resources, and optional extras.
- [x] T010 [US1] Remove redundant `backend/src/hatchling/plugin.py` and `scripts/stage_frontend.py` after artifact ownership moves to `hatch_build.py`.
- [x] T011 [US1] Verify root builds, archive-only rebuilding, installed Gunicorn, and standalone resources using `tests/packaging/` and `tests/server/integration/test_standalone_smoke.py`.

## Phase 4: US2 — Root development (P1)

**Independent test**: Root uv/pnpm/Task commands find the canonical projects and tests; Python editable installation works without JavaScript.

- [x] T012 [P] [US2] Move frontend manifests/configuration to root and application/public files to `src/frontend/`.
- [x] T013 [US2] Move utility scripts and codegen into `src/frontend/tooling/` and update their root/output calculations.
- [x] T014 [US2] Update Vite, HTML, Tailwind, lint/format, aliases, test setup, and browser/Node/Functions type scopes in root configuration files.
- [x] T015 [US2] Move Python suites into `tests/`, retain colocated React/utility tests, and move approved PNGs into `tests/frontend/snapshots/baselines/`.
- [x] T016 [US2] Update Python/frontend task definitions in `taskfiles/` while preserving existing public namespaces and preventing recursive root task calls.
- [x] T017 [US2] Fix path-sensitive API-generation, integration-smoke, and snapshot references in `tests/` and `src/frontend/tooling/`.
- [x] T018 [US2] Update root `.gitignore`, remove tracked compiler/report output, and eliminate obsolete root project/tooling directories.
- [x] T019 [US2] Verify root language checks, tests, API drift, snapshot tools, and no-JavaScript editable behavior through `Taskfile.yaml`.

## Phase 5: US3 — Deployment definitions (P2)

**Independent test**: Consolidated container definitions retain service/storage contracts; installed Gunicorn and nested credential-free Pages validation work.

- [x] T020 [P] [US3] Consolidate shared build stages and backend/frontend runtime targets in root `Dockerfile` and `.dockerignore`.
- [x] T021 [US3] Consolidate services/storage in root `docker-compose.yaml`, moving infrastructure files into `deploy/`.
- [x] T022 [US3] Update `docker-bake.release.hcl` and `tests/release.test.mjs` for root context, complete build fixtures, and existing version/tag contracts.
- [x] T023 [P] [US3] Add pinned Wrangler via pnpm, nested `src/frontend/wrangler.jsonc`, and `src/frontend/functions/` discovery.
- [x] T024 [US3] Add root Pages check/dev tasks and local synthetic proxy/config tests in `src/frontend/tooling/` and `tests/frontend/`.
- [x] T025 [US3] Update `.github/` caches, setup ordering, working directories, artifact paths, and `.pre-commit-config.yaml`.
- [x] T026 [US3] Verify rendered Compose parity, Bake plans, both Docker targets, Pages bundling/local HTTP, and root release behavior.

## Phase 6: US4 — Docs and Spec-Kit (P2)

**Independent test**: Features create/resume/plan/task under `docs/specs`; moved local links resolve and agent integrations share one source.

- [x] T027 [P] [US4] Add disposable feature lifecycle regressions in `tests/test_specify_workflows.py` and demonstrate the current creation-root mismatch.
- [x] T028 [US4] Move historical `specs/` into `docs/specs/` and current guides into `docs/{development,architecture,operations}/` plus root roadmap/checklist.
- [x] T029 [US4] Update creation defaults, numbering, and guidance in `.specify/scripts/bash/`, `.specify/templates/`, and `.gemini/commands/`.
- [x] T030 [US4] Repair documentation links, reconcile current runtime/setup instructions, and make `CLAUDE.md`/`GEMINI.md` point to `AGENTS.md`.
- [x] T031 [US4] Verify saved-state/override/no-persist behavior, task/plan setup, numbering, and local documentation links in `tests/test_specify_workflows.py`.

## Phase 7: Integration and closure

- [x] T032 Run root fix/lint/type/test/pre-commit gates and all explicit smoke/snapshot acceptance entrypoints defined in `quickstart.md`.
- [x] T033 Record build sizes/timings and actual validation evidence in `docs/specs/013-root-project-layout/quickstart.md`.
- [x] T034 Update feature status, task markers, and global `docs/CHECKLIST.md`; update the existing PR title/body to describe the implemented result.

## Dependencies and parallel execution

T001–T002 precede implementation. Capture failing tests while establishing each component's paths. Python packaging (T005–T011), frontend (T012–T014, T023–T024), deployment/CI (T020–T022, T025), and docs/Spec-Kit (T027–T031) have distinct file owners and can proceed concurrently. Root task integration and complete artifact/container validation depend on their combined results. T032–T034 follow all stories.

The first consumer deliverable is US1's complete artifact contract, supported by the root source moves in US2. All four stories are in this implementation's scope. Do not publish or modify hosted deployment settings during validation.
