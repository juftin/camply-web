# Implementation Plan: Root Project Layout

**Branch**: `innocent-lizard` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)
**Status**: Design complete; implementation not started
**Input**: `docs/specs/013-root-project-layout/spec.md`
**Baseline**: `origin/main` = `HEAD` = `25c9763`

## Summary

Turn the repository into one root Python project and one root JavaScript project. Move Python into `src/camply`, React directly into `src/frontend`, and frontend utilities/Pages Functions into that frontend tree. Retain the existing internal Python architecture, runtime extras, application contracts, and deployment identities.

Keep Hatchling and replace the wheel-only hook with a small root `hatch_build.py` handling complete sdist and wheel builds. Checkout builds compile the UI; source archives carry prepared assets for Python-only wheel rebuilding. Map generated assets into archives explicitly, without writing them into working application source.

Consolidate deployment into one root multi-stage Dockerfile and one Compose file. Package Gunicorn configuration as `camply.server.gunicorn`. Add `src/frontend/wrangler.jsonc` and root Tasks that run Wrangler in the nested Pages project. Relocate current documentation and historical specs, preserving Spec-Kit feature discovery and numbering.

## Technical Context

**Language/Version**: Python >=3.11; development/primary CI/builds use 3.14 with explicit 3.11 compatibility checks. Node 24 and existing `pnpm@12.15.0` pin. Preserve existing React/TypeScript/Vite versions.

**Primary Dependencies**: Existing uv, Hatchling, FastAPI, SQLAlchemy, Alembic, Celery, Vite/Vitest, native TypeScript, and go-task. Add `build` using `uv add --dev build`; add a pinned Wrangler development dependency using pnpm. No unrelated upgrades or new build backend.

**Storage**: Existing SQLite/PostgreSQL data and Alembic graph unchanged; preserve Compose named volumes and `.data/camply` mappings.

**Testing**: pytest, installed-artifact matrix on 3.14/3.11, import-linter, Vitest, API drift checks, snapshot/browser smoke checks, release tests, Docker Bake/Compose validation, and new credential-free Pages/Spec-Kit regressions.

**Target Platform**: Existing macOS/Linux development, supported Python consumers, Linux containers, and Cloudflare Pages. Gunicorn retains its existing platform marker; standalone remains the cross-platform server entrypoint.

**Project Type**: One application distribution with a browser frontend and multiple deployment modes.

**Performance Goals**: No runtime performance change. One frontend compilation per ordinary sdist-first build; no JavaScript work for editable installs, unchanged-sdist rebuilding, or wheel installation. Measure artifact sizes/build durations as evidence rather than inventing a threshold.

**Constraints**: No new public APIs, schema revisions, scheduler design, authentication behavior, provider behavior, or production publication. Normal builds must work without Task/Docker; all contributor workflows remain accessible through Task.

**Scale/Scope**: One Python manifest/lock, one JavaScript manifest/lock, two included Taskfiles, one Dockerfile, one Compose file, current docs/specs, and all path-sensitive tests/CI/release definitions.

## Constitution Check

Gate reviewed before research and again after design:

| Principle                              | Assessment                                                                                                                                                                                                       |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I. Reliability & Precision             | Pass: no provider, scheduling, or notification behavior changes. Existing behavior tests remain required.                                                                                                        |
| II. Type Safety & Static Analysis      | Pass: retain Python checks and current Oxlint/Oxfmt/native TypeScript gates; scope browser, Node-tooling, and edge source explicitly.                                                                            |
| III. Modern Workflow & Automation      | Pass: preserve Task wrappers and locked uv/pnpm environments; standard packaging also works independently.                                                                                                       |
| IV. Monorepos & Separation of Concerns | User-authorized amendment required: the literal `backend/`/`frontend/` rule conflicts with the approved target. Phase 0 changes it to `src/camply`/`src/frontend` while retaining all dependency-boundary rules. |
| V. Automated Verification              | Pass: meaningful artifact, workflow-discovery, Pages, and deployment regressions accompany the moves.                                                                                                            |

The current constitution is not silently treated as already amended. Implementation begins by updating principle IV, incrementing 2.0.0 to 3.0.0 for replacement of the mandated directory boundary, and recording the Sync Impact Report/template changes. The user's explicit layout instruction authorizes this scoped replacement; no additional approval is inferred. This planning-only change leaves current governance text intact.

## Project Structure

### Documentation for this feature

```text
docs/specs/013-root-project-layout/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── packaging.md
    └── deployment.md
```

Task generation is a subsequent Spec-Kit phase; this deliverable does not create `tasks.md` or start implementation.

### Target repository structure

```text
/
├── .dockerignore, .gitignore, .env.example, .envrc
├── .python-version, .node-version
├── .oxfmtrc.json, .oxlintrc.json, .pre-commit-config.yaml
├── .releaserc.json
├── AGENTS.md, CLAUDE.md -> AGENTS.md, GEMINI.md -> AGENTS.md
├── README.md, LICENSE
├── pyproject.toml, uv.lock, hatch_build.py, alembic.ini
├── package.json, pnpm-lock.yaml, pnpm-workspace.yaml
├── vite.config.ts, postcss.config.js, tailwind.config.js
├── tsconfig.json, tsconfig.node.json, tsconfig.snapshots.json, tsconfig.functions.json
├── Dockerfile, docker-compose.yaml, docker-bake.release.hcl
├── Taskfile.yaml
├── taskfiles/
│   ├── python.yaml
│   └── frontend.yaml
├── deploy/
│   ├── entrypoint.sh, nginx.conf, nginx.main.conf
│   └── monitoring/prometheus/prometheus.yml
├── src/
│   ├── camply/
│   │   ├── __init__.py, __about__.py, py.typed
│   │   ├── cli/
│   │   ├── db/{data,models,migrations}/
│   │   ├── providers/{recreation_gov,usedirect}/
│   │   ├── server/
│   │   │   ├── gunicorn.py, py.typed
│   │   │   └── {models,routers,services}/
│   │   └── worker/{engine,notifications,tasks}/
│   └── frontend/
│       ├── index.html, main.tsx, App.tsx, App.css, index.css
│       ├── components/, hooks/, lib/api/generated/schema.ts, pages/
│       ├── public/{_routes.json,favicon.ico,favicon.svg,branding/}
│       ├── test/{setup.ts,*.test.ts[x],__snapshots__/}
│       ├── functions/api/[[path]].ts
│       ├── tooling/{codegen.ts,snapshot-gallery.html,*.ts}
│       └── wrangler.jsonc
├── tests/
│   ├── {cli,db,providers,server,worker,packaging}/
│   ├── test_import_boundaries.py, release.test.mjs
│   └── frontend/snapshots/baselines/*.png
├── docs/
│   ├── PLAN.md, CHECKLIST.md
│   ├── development/, architecture/, operations/, images/
│   └── specs/NNN-feature-name/
├── .github/{actions,workflows}/
├── .gemini/commands/speckit.*.toml
└── .specify/{scripts,templates,memory,integrations,workflows}/
```

Ignored local output: `.venv/`, `node_modules/`, `.data/`, `.wrangler/` state wherever Wrangler creates it, `.specify/feature.json`, `build/frontend/`, `build/frontend-manifest.json`, `build/openapi.json`, `dist/`, `tmp/`, and compiler/test caches. Snapshot reports/captures belong in `tmp/snapshots`; only approved PNG baselines and textual DOM snapshots stay tracked.

**Structure Decision**: Keep runtime Python resources with their import packages, browser source and frontend-specific utilities with the frontend, infrastructure under `deploy`, and project manifests/tooling entrypoints at root. Do not introduce replacement root `scripts` or `functions` directories.

## Migration Map

| Current location                                                                                | Target/action                                                                                     |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `backend/{pyproject.toml,uv.lock,.python-version,alembic.ini}`                                  | Root; reconcile lock through uv without unrelated resolution changes.                             |
| `backend/src/camply`                                                                            | `src/camply`; retain import paths, `py.typed`, seeds, templates, and migration IDs.               |
| `backend/src/hatchling/plugin.py`                                                               | Replace with root `hatch_build.py`; do not keep a stray import package named `hatchling`.         |
| `backend/config/gunicorn.conf.py`                                                               | `src/camply/server/gunicorn.py`.                                                                  |
| `backend/tests`                                                                                 | Root `tests`; preserve package markers, fixtures, cassette layout, and nested integration suites. |
| `frontend/{package.json,pnpm-*,.node-version,.*lint*,vite.config.ts,*config*.json,*config*.js}` | Corresponding root manifests/configuration; root `.oxfmtrc.json` is updated in place.             |
| `frontend/src/*`                                                                                | `src/frontend/*`; React tests stay colocated.                                                     |
| `frontend/{index.html,public,functions}`                                                        | Under `src/frontend`.                                                                             |
| `frontend/scripts/*`, `frontend/src/lib/codegen.ts`                                             | `src/frontend/tooling`; retain utility tests beside utilities.                                    |
| `frontend/snapshots/baselines`                                                                  | `tests/frontend/snapshots/baselines`.                                                             |
| `frontend/snapshots/REPORT.md` and transient captures                                           | Regenerate under ignored `tmp/snapshots`; remove the tracked generated report.                    |
| `frontend/tsconfig.tsbuildinfo`                                                                 | Remove from tracking; preserve ignore rule.                                                       |
| Nested Taskfiles                                                                                | `taskfiles/python.yaml` and `taskfiles/frontend.yaml`; retain public namespaces.                  |
| Nested Dockerfiles, `.dockerignore` files, Compose files                                        | Consolidate into one of each at root; preserve release Bake overlay.                              |
| Entrypoint, Nginx, Prometheus configuration                                                     | Corresponding paths under `deploy`.                                                               |
| Duplicate backend README/license                                                                | Merge applicable instructions into root README/developer guide; retain root license.              |
| `scripts/stage_frontend.py`                                                                     | Remove after the build hook owns artifact inclusion.                                              |
| `specs/*`                                                                                       | `docs/specs/*`, alongside this already-created feature.                                           |
| `docs/agents/{PLAN,CHECKLIST}.md`                                                               | `docs/`.                                                                                          |
| Developer/style/troubleshooting/agentic guides                                                  | `docs/development/`; preserve filenames.                                                          |
| Architecture/dependency/API/provider/frontend/notification designs                              | `docs/architecture/`; preserve filenames.                                                         |
| Configuration and release guides                                                                | `docs/operations/`; preserve filenames.                                                           |

## Design Decisions

### Root development and task execution

The root Taskfile keeps orchestration, releases, API generation, and Compose commands. It includes Python and frontend task definitions using explicit repository-root working directories. Preserve `backend:*`, `frontend:*`, `standalone:*`, snapshot, release, and smoke-test names. Included tasks that currently call an unqualified nested `task test` must be rewritten to target the intended namespace; otherwise root `test` would run the entire monorepo or recurse.

Python uses root uv metadata/environment; remove `--project backend` and nested CI working directories. Scope mypy to `src/camply` plus the build hook where appropriate. Keep import-linter contracts and optional-extra installation tests. Add `build` with uv so `uv run python -m build` works after setup; bare `python -m build` requires that same environment's interpreter.

Frontend package scripts run at root. Vite's `root` is `src/frontend`, its `publicDir` remains `public` relative to that root, and its output is absolute/root-resolved `build/frontend`. Update the HTML entry from `/src/main.tsx` to `/main.tsx`, the `@` alias, setup paths, Tailwind content globs, generated-type destinations, and all smoke-tool working directories.

Use precise TypeScript scopes: browser checks exclude `tooling` and `functions`; `tsconfig.node.json` checks Vite and Node utilities; `tsconfig.snapshots.json` retains snapshot-tool checks; a small `tsconfig.functions.json` checks only `src/frontend/functions` using standard worker/web types and no ambient Node/test globals. Avoid a broad `include: ["src"]`. Root scripts run every configured project, and lint includes utilities/Functions that were previously omitted.

### Complete Python artifacts

The authoritative rules are in [contracts/packaging.md](contracts/packaging.md). Hook execution is restricted to standard sdist/wheel builds. Editable builds return before probing or invoking JavaScript tools; dependency discovery and supported metadata-only paths remain lightweight. A frontend's actual standard-wheel metadata fallback is still a full build.

Each checkout build clears only its own frontend output, invokes pinned pnpm with `install --frozen-lockfile`, and builds root-hosted `/api` assets. The hook uses absolute paths derived from its build root, not the current working directory or a sibling checkout. There is no npm fallback or automatic toolchain download. Failure messages identify the missing tool or failing operation.

Use a small generated manifest for bundled assets, containing package/build-recipe versions, frontend-input digest, and the asset path/checksum inventory. Identify an archive build using its root `PKG-INFO` plus the generated manifest, not Git availability. Validate assets and input digests before reuse; corrupted/inconsistent archive assets fail with a rebuild explanation. Checkout builds never reuse that archive shortcut.

Force-map `build/frontend` into `src/camply/server/static` in the sdist and into `camply/server/static` in the wheel. Include the manifest in the sdist as `build/frontend-manifest.json`; do not expose it as a served UI file. Whitelist frontend source/public/tooling inputs, root manifests/locks, build hook and referenced TS/Vite/PostCSS/Tailwind configuration in the sdist. Exclude dependencies, output trees except the explicit manifest/assets, tests' screenshot baselines, reports, operational data, and secrets. Prevent default source traversal from also selecting the mapped static destination.

Source-archive rebuilding validates and reuses its UI without Node; changing frontend inputs in an extracted archive invalidates reuse and requires a fresh source build with the documented tools. Artifact tests cover source-first builds, direct wheels, archive rebuilding, missing tools, corrupt assets, changed inputs, deleted assets, root paths, and lazy map workers.

### Containers and Gunicorn

Use one multi-stage Dockerfile with a build stage containing Python 3.14, Node 24, pinned pnpm, and uv. Run the same root packaging path there; build tools remain outside runtime images. The frontend runtime target copies generated assets into the existing Nginx image layout; the backend target installs the built wheel with existing distributed-deployment extras. Retain locked runtime dependencies, for example by syncing dependencies with `--no-install-project` before installing the wheel without dependency re-resolution. Do not use an editable source installation in the runtime image.

Keep `ghcr.io/juftin/camply-backend` and `ghcr.io/juftin/camply-frontend`, Bake target names, release tags, and frontend build arguments. The common root-hosted frontend build is shared where settings match; distinct build arguments must not reuse mismatched assets. No Node, pnpm, or frontend development dependencies are copied into either runtime target.

Merge included Compose definitions with their resolved paths, not literal blind concatenation. Preserve `db_data`, `valkey_data`, `prometheus_data`, project name `camply`, `.data/camply` mounts, readiness dependencies, commands, and operational defaults. Compare rendered normalized configuration before/after, allowing only intentional build/config source-path differences.

Move Gunicorn code without changing its settings; invoke `gunicorn --config python:camply.server.gunicorn camply.server.app:app` from tasks and containers. Verify `--check-config` on a supported installed server environment. Its placement under `server` preserves import-linter's exhaustive component classification.

### Pages and Wrangler

Create the real `src/frontend/wrangler.jsonc` during implementation with the exact baseline in [contracts/deployment.md](contracts/deployment.md): Pages project `camply-81r`, output `../../build/frontend`, compatibility date `2024-11-11`, and root-installed Wrangler schema. Keep backend origin externally supplied and preserve production/preview bindings when introducing file-based configuration. The date retains the existing documented Fetch cache requirement rather than changing runtime semantics incidentally.

Root Tasks `frontend:pages:check` and `frontend:pages:dev` invoke the pinned root Wrangler using `--cwd src/frontend`. Build validation bundles Functions into `tmp/pages-functions`; local serving uses built assets and requires no Cloudflare login. Tests prove config-relative output and nested Function discovery. Keep `_routes.json` copied into output and include `/api` and `/api/*`.

For Git-integrated Pages, set project root to `src/frontend`, invoke the root frozen install/build from there, and use the config's output. Explicitly select the existing Node/pnpm pins in that environment because the version files now live above its project root. Document that these dashboard root/build settings and existing environment bindings require operator migration; a Wrangler file does not configure every Pages dashboard field. No hosted configuration or deployment is changed by this feature's local validation.

### Spec-Kit and documentation

Move historical directories with their names and duplicate numeric prefixes intact; this feature already lives in the destination. Change the shell feature creator's default and Gemini specify command's scanning/creation instructions to `docs/specs`. Update plan/task templates and guidance. `SPECIFY_FEATURE_DIRECTORY` remains an explicit full-feature-directory override, not a new global specs-root setting. Keep `.specify` at root and `.specify/feature.json` ignored.

Update stale local saved pointers only when they reference the moved old root and the destination exists; document how other checkouts select the relocated feature. Do not commit per-machine state or introduce a root `specs` symlink. Regression fixtures cover creation, numbering, explicit overrides, relative saved pointers, setup-plan/setup-tasks, and read-only/no-persist behavior. Record modified managed defaults so future Spec-Kit refreshes can be checked for drift.

Relocate current guides according to the migration map and repair local links from READMEs, agent instructions, current docs, and historical specs. Preserve historical descriptions of previous layouts. Fix current contradictions about standalone support and outdated package-manager guidance. Point Gemini and Claude at canonical `AGENTS.md`; preserve Spec-Kit's separate command integration files.

## Implementation Sequence and Verification

1. **Governance and regression baseline**: Amend the directory principle and templates, capture current task/service/publication inventories, and add failing artifact/discovery/path regressions in disposable fixtures. Verify failures demonstrate missing UI/source-first/root behavior rather than unrelated service outages.
2. **Root Python project**: Move manifest/lock/source/tests, install `build` through uv, package Gunicorn, and update Python task/CI paths. Verify root editable installation without JavaScript, imports/extras, migrations, and Python quality/tests.
3. **Root frontend project**: Move manifests/source/tooling/functions/baselines, update all root scripts/configuration/path calculations, and add pinned Wrangler through pnpm. Verify frontend lint/type/tests, API drift, utility tests, and unchanged snapshots.
4. **Complete distributions**: Replace hook/stager with archive inclusion and validation, then update release artifact fixtures. Verify ordinary `python -m build`, direct wheel, toolchain-free archive rebuild, clean installs, and standalone browser behavior.
5. **Deployment consolidation**: Add one Dockerfile/Compose/root ignore file, move infrastructure config, update Bake/release tests, and add nested Wrangler config/tasks. Verify rendered config parity, both runtime image builds, Gunicorn loading, and credential-free Pages checks.
6. **Docs and Spec-Kit migration**: Move historical specs/current docs, fix links and creation defaults, consolidate agent instructions, remove tracked generated caches/reports and obsolete directories. Verify feature workflow regressions and local links in a disposable checkout.
7. **CI/release closure**: Update caches, working directories, interpreter environment paths, upload locations, setup ordering, source fixtures, and version stamping. Add frontend setup to packaging/compatibility/release jobs that now compile UI; Python-only editable/test/lint jobs remain independent. Pass the full validation matrix and update the global checklist.

Use reviewable commits within one feature branch; intermediate commits need not be independently releasable. Deployment rollout occurs only after the complete path migration is verified. No new database migration is required.

## Validation Matrix

| Scope / requirements                         | Checks required during implementation                                                                                                                                                                                        |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Root projects and tasks: FR-001–003, 008–011 | `task --list-all`, root uv/pnpm discovery, editable install with JavaScript unavailable, task inventory/namespace checks, no generated source dirt.                                                                          |
| Complete artifacts: FR-004–009, 014, 020     | `uv run python -m build`; direct wheel; archive-only rebuild with JS executables unavailable; artifact inventory/digests; installed base/server/worker matrices on 3.14 and 3.11; installed Gunicorn on supported platforms. |
| Frontend contract: FR-011, 016, 020–021      | `task frontend:test`, `task api:check`, `task snapshot:verify`, `task snapshot:check`, lazy worker/browser checks, proxy cookie/redirect/error regressions.                                                                  |
| Deployment: FR-012–016                       | Explicit-env `docker compose config` without reading secret files, Docker Bake plans, both image targets, existing service/volume checks, `task frontend:pages:check`, local Pages HTTP fixture.                             |
| Spec-Kit/docs: FR-017–019, 022               | Disposable feature create/number/resume/setup tests; saved-state/override/no-persist checks; local Markdown link verification; canonical agent pointers; constitution/template alignment.                                    |
| End-to-end and CI: FR-020–021                | `task fix`, `task lint`, `task check`, `task test`, pre-commit, API drift, standalone/admin/maps/PostgreSQL smoke entrypoints, release fixtures and actionlint where available.                                              |

The browser/database integration entrypoints remain explicit, with their existing CI jobs. Do not silently turn all opt-in live tests into ordinary unit-suite dependencies or drop them because paths moved. Ordinary package tests must install prebuilt wheels without development dependencies and run outside the checkout. New Pages/Spec-Kit checks must be wired into `task test`/CI, not merely described as manual commands.

## Risks, Drawbacks, and Recovery

- Every consumer downloads UI assets, including provider-only/worker installations. Accept one coherent distribution; do not add a second package or optional asset-download mechanism.
- Complete checkout/release artifact builds now require Node/pnpm and locked JavaScript dependencies. Cache dependency stores in CI, preserve Python-only editable workflows, and document prerequisites.
- The sdist contains source plus prepared assets, increasing size and requiring an explicit archive manifest/inclusion contract. Verify exact expected file sets and remove obsolete output before rebuilding.
- Consolidation broadens root Docker context and configuration scope. Root `.dockerignore`, precise copy steps, lint/type globs, and archive whitelists prevent accidental data/dependency inclusion.
- Pages configuration and moved document links are externally/path sensitive. Exercise nested config locally and document operator-side Pages settings; do not infer live binding values.
- Rollback reverts source/configuration moves together and restores the prior Pages build-root settings if already changed. Existing database contents/revision history and Docker volumes are retained; no data migration rollback is necessary.

## Complexity Tracking

| Constitution conflict                       | Why needed                                                                                                                                                      | Alternative considered                                                              |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Principle IV's literal nested project roots | The user explicitly approved root manifests with `src/camply` and `src/frontend`. Amend the directory wording before implementation while retaining boundaries. | Retaining nested roots would defeat the approved root packaging/workflow objective. |

Post-design check: all non-directory constitution requirements remain satisfied. The one documented, user-authorized amendment is the first implementation step; there are no unresolved design clarifications.
