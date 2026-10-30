# Tasks

- [x] Add the static-directory CLI and unit/installed-artifact coverage.
- [x] Combine Python and Nginx in one image and serve package-owned assets directly.
- [x] Preserve independent role startup and test migration dispatch.
- [x] Unify Compose image/build settings, Task builds, release tags, and Docker CI.
- [x] Publish four release tags: major version, full version with `v` prefix, seven-character Git SHA, and `latest`; verify rendered publication plans and required revision input.
- [x] Update release regressions, deployment documentation, and the global checklist.
- [x] Complete final checks and shared-container smoke verification.

Validation: `task test`, `task lint`, `task check`, changed-file pre-commit hooks, and Actionlint passed. A shared runtime built from the locally prepared wheel passed CLI, worker/beat command, default API/migration, and Nginx static/SPA/health/API-proxy checks as the non-root `camply` user. The full source Docker build hit local storage exhaustion during frontend dependency installation; its runtime stages were verified separately with that real wheel.
