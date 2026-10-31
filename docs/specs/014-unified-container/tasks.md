# Tasks

- [x] Resolve bundled frontend assets internally with unit/installed-artifact coverage.
- [x] Combine Python and Nginx in one image and serve package-owned assets directly.
- [x] Preserve independent role startup and test migration dispatch.
- [x] Unify Compose image/build settings, Task builds, release tags, and Docker CI.
- [x] Publish four release tags: major version, full version with `v` prefix, seven-character Git SHA, and `latest`; verify rendered publication plans and required revision input.
- [x] Update release regressions, deployment documentation, and the global checklist.
- [x] Complete final checks and shared-container smoke verification.

- [x] Add behavior coverage for all four `camply serve` roles.
- [x] Package and render Nginx configuration at runtime, replacing the CLI process with foreground Nginx.
- [x] Add backend and worker process launchers while preserving migration and initialization behavior.
- [x] Adopt role commands in Docker/Compose and update installation/deployment documentation.
- [x] Consolidate all runtime launchers under `camply serve frontend/backend/worker/beat`.
- [x] Verify the role launchers, package resources, runtime smoke, and quality gates; update the PR.
- [x] Make bare `camply serve` start the standalone application, with listener options, existing resource validation/migrations/local scheduling, and installed-package HTTP coverage.
- [x] Validate role dependencies before startup and run Python servers from the CLI interpreter; test partial extras, unrelated executables, and an installed backend with an empty `PATH`.
- [x] Preserve both existing required Docker check names while building the shared image once; reject failed, cancelled, or skipped builds in the frontend check.
- [x] Configure role-specific graceful shutdown signals and a one-minute Compose grace period; verify live HTTP cleanup, direct standalone SIGKILL/PID ownership, and SQLite integrity, and document host process-group supervision.

Validation: CLI, entrypoint, installed-wheel/sdist resources, optional dependency boundaries, and rendered release/Compose plans passed. A shared runtime built from the real local wheel passed frontend/backend startup, API migrations and proxying, wheel-identical assets, SPA routes, worker/beat argument forwarding, non-root operation, and graceful shutdown. Lint, types, pre-commit hooks, and ShellCheck passed. The full source Docker build passed in CI; local Docker builds remain constrained by available storage.
