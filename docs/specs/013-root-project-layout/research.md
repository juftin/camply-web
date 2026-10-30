# Research: Root Project Layout

**Date**: 2026-10-29
**Baseline**: `25c9763`; local files and primary documentation reviewed before design.

## 1. Preserve the existing distribution and runtime boundaries

**Decision**: Move the project root without changing the `camply` package architecture or extras.

**Evidence**: [Python metadata](../../../pyproject.toml) defines one distribution with `server`, `distributed`, `postgres`, and `sentry` extras, and import-linter protects optional dependencies. [Standalone launcher](../../../src/camply/server/standalone.py) already validates installed UI resources and supports an external absolute asset directory. [Constitution](../../../.specify/memory/constitution.md) principle IV still mandates nested roots.

**Rationale**: The recent package/standalone work already supplies the necessary runtime architecture. A directory/build migration should preserve it.

**Alternatives considered**: Separate UI distribution, optional downloaded assets, renamed runtime packages, or moving shared scheduler modules. All add scope unrelated to the requested root layout.

## 2. Build complete source archives before wheels

**Decision**: Keep Hatchling; use a standard-build hook for both targets, explicitly map generated assets into archives, and validate bundled output before source-archive reuse.

**Evidence**: The current [baseline hook](https://github.com/juftin/camply-web/blob/25c9763/backend/src/hatchling/plugin.py) only handles standard wheels, looks outside the Python project, can skip missing sources/tooling, and stages output into an ignored source directory. The [sdist whitelist](../../../pyproject.toml) omits frontend siblings. `python -m build` normally creates an sdist and builds its wheel from the extracted archive. [PyPA build documentation](https://build.pypa.io/en/stable/how-to/basic-usage.html)

Hatch supports build-data forced inclusion and explicit generated artifacts. Default file selection respects version-control ignore rules. [Hatch hook interface](https://hatch.pypa.io/latest/plugins/build-hook/reference/), [Hatch file selection](https://hatch.pypa.io/latest/config/build/)

**Rationale**: The source archive must be sufficient to build the application independently. A small input/output manifest prevents corrupted or changed archives from silently reusing inconsistent UI assets. Editable paths return before toolchain probing.

**Alternatives considered**: Wheel-only hooks fail source-first completeness; always rebuilding JavaScript from sdists adds a consumer toolchain requirement; committing compiled UI creates routine source churn; changing build backends is unnecessary.

**Metadata nuance**: Hatchling exposes metadata-only hooks in supported contexts and builds editable wheels through a distinct version. Some package frontends may fall back to an actual standard wheel build for metadata; that operation must still produce a complete application. [Hatchling build frontend hooks](https://raw.githubusercontent.com/pypa/hatch/master/backend/src/hatchling/build.py)

## 3. Use one Dockerfile with existing runtime images

**Decision**: Share application build stages and retain separate backend/frontend runtime targets and existing image names.

**Evidence**: Root Compose currently includes two project-relative Compose files; backend/worker/beat share the backend image. The Bake release overlay and release tests assume backend/frontend target identities. [Compose entrypoint](../../../docker-compose.yaml), [release overlay](../../../docker-bake.release.hcl), [release tests](../../../tests/release.test.mjs)

**Rationale**: The user requested definition consolidation, not deployment-topology changes. Explicit root contexts and normalized before/after configuration checks protect mounts and environment semantics.

**Alternatives considered**: One combined API/Nginx/worker image or a standalone-only stack would change delivery behavior. Retaining nested Dockerfiles/Compose includes conflicts with the accepted plan.

## 4. Install Gunicorn configuration as an importable module

**Decision**: Move the existing settings into `camply.server.gunicorn` and use Gunicorn's `python:` configuration syntax.

**Evidence**: Current settings live outside the import package and task/container commands reference a file path. Gunicorn accepts `python:MODULE_NAME` for configuration. [Current settings](../../../src/camply/server/gunicorn.py), [Gunicorn settings reference](https://gunicorn.org/reference/settings/#config)

**Rationale**: Installed packages can resolve configuration regardless of their working directory. Keeping it under `server` preserves current optional-runtime boundaries.

**Alternatives considered**: Copying configuration beside site-packages or locating source files at runtime retains deployment-specific filesystem assumptions.

## 5. Keep Pages Functions and Wrangler with frontend source

**Decision**: Put `wrangler.jsonc` and `functions` under `src/frontend`; run root-installed Wrangler with that working directory. Retain project `camply-81r`, a config-relative output path, and the already-documented cache-compatible date `2024-11-11`.

**Evidence**: Pages Functions use a `functions` directory at the Pages project root. Wrangler supports Pages output/date/project configuration, working-directory selection, and local Function bundling. [Function placement](https://developers.cloudflare.com/pages/functions/get-started/), [Pages configuration](https://developers.cloudflare.com/pages/functions/wrangler-configuration/), [Wrangler Pages commands](https://developers.cloudflare.com/workers/wrangler/commands/pages/)

The current proxy uses externally supplied `CAMPLY_API_ORIGIN`, requires HTTPS, rewrites upstream redirects, and forwards cookies. Existing docs identify the project, preview trust policy, and minimum runtime date. [Proxy](../../../src/frontend/functions/api/[[path]].ts), [current operator guide](../../operations/CONFIGURATION.md)

**Rationale**: This removes unwanted root folders while retaining framework discovery. The checked-in config must be validated with both preview/production bindings before eventual publication; no live values are inferred.

**Alternatives considered**: Root `functions` violates the user's final layout. A static-only upload would omit the cookie-preserving proxy. Migrating to Workers advanced mode would change deployment architecture unnecessarily.

## 6. Relocate specs through existing feature-path support

**Decision**: New feature 013 is created directly under `docs/specs`; move old features and update creation/numbering defaults during implementation. Keep `.specify` at root and feature state checkout-local.

**Evidence**: The installed version is 1.1.3. [Path resolver](../../../.specify/scripts/bash/common.sh) honors explicit feature directories and `.specify/feature.json`; [creator](../../../.specify/scripts/bash/create-new-feature.sh) and [Gemini specification command](../../../.gemini/commands/speckit.specify.toml) still default to root `specs`. Spec-Kit's upstream documents the independent project-root and active-feature-directory axes. [Core reference](https://github.com/github/spec-kit/blob/main/docs/reference/core.md)

**Rationale**: Existing plan/task/prerequisite scripts already support the selected location. Creation and next-number scanning require deliberate changes, tested in temporary repositories. Existing duplicate number prefixes remain untouched.

**Alternatives considered**: A root compatibility symlink retains unwanted structure; a custom global directory setting without tool support would provide false confidence; reinitializing Spec-Kit introduces unrelated changes.

## 7. Preserve test ownership and current instructions

**Decision**: Move Python suites to root `tests`, retain colocated React/utility tests, move PNG baselines outside source, and update actual path calculations rather than adding wrapper checkouts.

**Evidence**: Existing Python live tests calculate roots using fixed parent counts and run pnpm from `frontend`; release fixtures copy only Python sources; frontend codegen is currently in browser source. CI packaging/release jobs do not consistently install the frontend toolchain. `CLAUDE.md` is a symlink while `GEMINI.md` is a diverging copy.

**Rationale**: Path-sensitive checks and release fixtures must exercise the same complete artifacts that consumers receive. One instruction source and current-versus-historical documentation reduce future drift.

**Alternatives considered**: Moving all React tests into a central suite or refactoring Python component ownership creates unnecessary churn.

All design questions needed for planning are resolved. Real deployment bindings and publication are operator actions outside this deliverable.
