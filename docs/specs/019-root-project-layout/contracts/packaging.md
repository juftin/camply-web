# Contract: Complete Python Application Artifacts

## Entry points

| Operation                      | Required behavior                                                          |
| ------------------------------ | -------------------------------------------------------------------------- |
| Root `python -m build`         | Build sdist, then wheel from that sdist; exactly one pair in clean output. |
| Root `uv build` / `task dist`  | Same complete application contract; wrapper may clear stale `dist` first.  |
| Root `python -m build --wheel` | Complete direct checkout wheel.                                            |
| Extracted-sdist wheel build    | Complete wheel with no frontend toolchain or dependency installation.      |
| Editable Python installation   | Python-only; frontend resources are optional during development.           |

After root setup, `uv run python -m build` selects the project interpreter with the `build` development dependency. A bare Python interpreter must itself have that module installed. Build isolation provisions Python build dependencies; Node 24 and the pinned pnpm remain documented checkout-build prerequisites.

## Contents

### Wheel

- Existing `camply` modules, typing markers, provider seeds, full Alembic graph/templates, CLI entrypoints, and distribution metadata/license.
- Installed `camply/server/gunicorn.py`.
- `camply/server/static/index.html`, emitted assets/chunks/map worker, favicons, branding, and other public build files.
- No frontend source tree, Node dependencies, build hook, reports, screenshot baselines, operational databases, or secrets.
- Extras remain exactly `server`, `distributed`, `postgres`, and `sentry`; selecting one does not change file contents.

### Source distribution

- Python source/runtime resources, root metadata/license/readme, `hatch_build.py`, and needed developer Alembic configuration.
- Frontend source/public/tooling files, root package metadata and frozen lock/manager settings, version pins, and referenced build/TypeScript configuration, sufficient for a fresh frontend build when desired.
- Prepared UI mapped to `src/camply/server/static`, plus `build/frontend-manifest.json`.
- No dependency directories, incidental cached output, screenshots/reports, application data, or secret files. Explicit generated inclusion must survive normal ignore rules.

The wheel and sdist must derive from the same stamped package/frontend versions. The standard archive remains a pure-Python wheel with static data; no platform-specific UI binary is introduced.

## Build invariants

1. Resolve paths from the project root and invoke pnpm directly, never Task or Docker.
2. Source checkout builds always perform a frozen install and a fresh asset build; missing prerequisites fail clearly.
3. Set Python-served output to root base `/` and same-origin `/api`, irrespective of GitHub repository environment variables. Preserve explicitly supported public feature/map options in the build recipe.
4. Limit cleanup to generated output owned by this build. Do not modify `src/camply`, delete bundled source-archive resources, or remove arbitrary external frontend overrides.
5. Generate/validate the exact asset inventory and input digest described in [data-model.md](../data-model.md).
6. Reuse prepared assets only for an extracted archive with matching root package metadata, inputs, recipe, and inventory. Invalid archives fail with directions for a fresh source build; they never become UI-less wheels.
7. Exclude archive static destinations from ordinary traversal before force-mapping assets so they are included once.
8. Editable/dependency-discovery paths return without JavaScript work. Do not weaken standard-wheel completeness to accommodate metadata callers that actually build a wheel.

## Acceptance matrix

Exercise default root build, direct wheel, wheel rebuilt from an archive copied outside the repository, and clean installations of each relevant artifact. For the archive-only path, make Node/pnpm/npm unavailable or fail if invoked while leaving Python build tooling accessible.

Verify archive contents and versions, resource loading, optional-extra isolation, installed Gunicorn on supported platforms, actual static asset requests, client navigation fallback, `/api` errors remaining API errors, and lazy map worker availability. Delete or corrupt a recorded asset, change an input, remove the frontend toolchain, introduce stale output, and simulate lock/build failure to prove errors are actionable and incomplete artifacts are not produced.

Tests must use real built assets for the consumer path. Release fixtures must stop treating a Python-only source copy as a valid complete checkout.
