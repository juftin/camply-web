# Quickstart and Acceptance Validation

**Status**: These application commands describe the implemented target. They are not evidence that the migration is already implemented. Current design-document validation is recorded at the end.

## Prerequisites

- Python 3.14 and uv; Python 3.11 available for minimum-version verification.
- Node 24 and the pnpm version pinned in root `package.json`.
- go-task for contributor workflows; standard Python builds do not require it.
- Docker/Buildx for container and live-service checks; Chromium for browser checks.
- No production credentials, provider calls, hosted deployments, or notification delivery are needed for acceptance fixtures.

## 1. Install and discover root projects

```bash
task --list-all
task install
uv run camply --version
pnpm run typecheck
```

Expect one root Python environment and one root JavaScript dependency installation. Existing `backend:*` and `frontend:*` task names remain available. Separately test a fresh Python-only editable installation with JavaScript executables unavailable; installing it must not build or require UI assets.

## 2. Build complete distributions

From a clean tracked-source fixture with no previous build output or node_modules:

```bash
uv run python -m build
task backend:packaging:test
task backend:packaging:test PACKAGING_PYTHON=3.11
```

Expect one wheel and one sdist from the first command. Standard checkout builds perform their own frozen frontend install/build. The packaging suite must exercise both direct wheels and source-first builds, copy the source archive outside the repository, disable access to Node/pnpm/npm, rebuild its wheel, and install artifacts into fresh environments with only their selected extras.

Inspect the exact inventories in [contracts/packaging.md](contracts/packaging.md), including package markers, migration templates/revisions, packaged Gunicorn, index HTML, lazy chunks/map worker, branding, and matching version metadata. Verify there is no copied source/dependency tree in the wheel. Modify/delete an archived input/asset and confirm an actionable failure rather than incomplete output.

## 3. Run the installed complete application

```bash
task frontend:browser:install
task standalone:test
```

The smoke test must install the built wheel outside the checkout, use file-backed synthetic SQLite storage, and serve the home page, client deep link, asset/map worker, and API in a browser. It must not accidentally import editable checkout code or resolve assets from an old source directory. Check both direct and sdist-rebuilt artifact resources through the packaging/browser test combination.

For manual package use, install the actual wheel path with `[server]` into a fresh uv-created environment, then run its interpreter with:

```bash
python -m camply.server.standalone --port 8000
```

On a supported Gunicorn platform, use that installed environment to validate:

```bash
gunicorn --check-config --config python:camply.server.gunicorn camply.server.app:app
```

## 4. Check frontend behavior and Pages

```bash
task frontend:test
task api:check
task snapshot:verify
task snapshot:check
task frontend:pages:check
```

Expect unchanged approved visual baselines and API types unless a path-only fixture reference requires updating. Pages checks must discover `src/frontend/wrangler.jsonc`, resolve `../../build/frontend`, bundle the nested Function, and verify local routes/cookies/error responses without Cloudflare authentication. Temporary output belongs under `tmp`.

For manual local Pages serving:

```bash
task frontend:pages:dev
```

Without an injected backend origin, `/api` returns the existing configuration-error response. Automated forwarding/cookie/redirect checks use a test-owned upstream fixture and synthetic bindings. Do not read developer secret files as test inputs. Review [deployment contracts](contracts/deployment.md) before eventually changing hosted Pages root/build settings or publishing.

## 5. Check containers, services, and release plans

```bash
task build
task release:test
```

Expect backend/frontend targets from the same root Dockerfile, unchanged image identities/tag rules, and complete UI assets in both delivery paths. Compare normalized Compose configurations with explicit synthetic environment settings and env-file loading disabled. Verify service names, dependency ordering, ports, health checks, named volumes, and `.data/camply` mapping match the baseline. Build/runtime checks must confirm Node tooling is absent from final images.

Keep existing live checks explicit:

```bash
task search:smoke
task maps:verify
task admin:smoke
```

These use disposable services and synthetic fixtures. No production database, real provider account, or published image is part of the test.

## 6. Check Spec-Kit after migration

Run these lifecycle checks in a disposable fixture so creating test features does not change this checkout's active feature:

1. With migrated `docs/specs` directories present, run the feature creator and verify the next number, destination, generated spec, and saved relative pointer.
2. Resolve an existing feature via `SPECIFY_FEATURE_DIRECTORY=docs/specs/<feature>` and separately via `.specify/feature.json`.
3. Run `setup-plan.sh --json`, `setup-tasks.sh --json`, and prerequisite checks with appropriate spec/plan/task fixtures.
4. Confirm no root `specs` directory is created, read-only/no-persist resolution does not rewrite state, and duplicate historical numeric prefixes remain unchanged.
5. Check local Markdown links and both agent integration pointers; preserve historical prose about former layouts.

## 7. Complete quality gates

```bash
task fix
task lint
task check
task test
task pre-commit -- --all-files
```

Validate workflow syntax with actionlint where available. Inspect generated outputs and Git status; only intended source/config/document changes and approved fixtures should be tracked. Record size/build-duration measurements and acceptance evidence, then update the global checklist. Passing documentation checks alone does not complete any runtime requirement.

## Design-document verification

For this planning deliverable, the resolved spec/plan templates and `setup-plan.sh --json` were used with the new feature directory. Validation on 2026-10-29 covered:

- `check-prerequisites.sh --json --require-spec` resolved this feature and its research, model, contracts, and quickstart.
- All 43 local file links across the eight feature documents and global checklist resolved.
- FR-001–FR-022 were sequential and unique; no unresolved template markers or unbalanced code fences remained.
- The project's pinned Oxfmt 0.75.0 formatted the nine Markdown documents; its check and `git diff --check` passed.
- The source branch still matched the fetched `origin/main` baseline when planning began. Only design documents and the global checklist changed; the active-feature pointer is ignored checkout-local state.

Application builds, runtime suites, and hosted publication remain implementation work.
