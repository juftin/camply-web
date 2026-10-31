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
- [x] Support `CAMPLY_BACKEND_URL` in the frontend launcher and Compose, preserving the current default and Nginx variables; verify configuration rendering and synthetic upstream routing.

Validation: CLI, entrypoint, installed-wheel/sdist resources, optional dependency boundaries, and rendered release/Compose plans passed. A shared runtime built from the real local wheel passed frontend/backend startup, API migrations and proxying, wheel-identical assets, SPA routes, worker/beat argument forwarding, non-root operation, and graceful shutdown. Lint, types, pre-commit hooks, and ShellCheck passed. The full source Docker build passed in CI; local Docker builds remain constrained by available storage.

- [x] Gate Compose workers/beat on a healthy, migrated backend and verify fresh-database startup ordering.
- [x] Add opt-in provider-sync dispatch to the beat CLI, preserving expiry, error propagation, native arguments, dependency checks, and exec.
- [x] Use the beat option in Compose and update deployment guidance, installed-artifact tests, and the global checklist.

Fresh-start evidence: a source-mounted Python runtime with fresh test-owned PostgreSQL and Valkey volumes reached Alembic revision `4d64e0e4ae18`; Docker timestamps placed worker/beat startup after API health, and the broker held exactly one `camply.catalog.sync_all_providers` message with `expiration=600000`. The worker consumed a synthetic empty queue so no booking-provider requests ran. This exercises runtime code and Compose dependencies without rebuilding the final shared image.

- [x] Add `serve healthcheck` with standalone/backend/frontend HTTP probes and bounded local-worker inspection.
- [x] Add beat scheduler heartbeat generation and freshness/PID checks; adopt all role probes in Compose.
- [x] Verify failure modes, clean installed HTTP probes, and real worker/beat health lifecycle with a disposable broker in local/CI workflows.
- [x] Complete quality checks, documentation/checklist updates, and the PR description.

Healthcheck validation: 761 Python tests passed (20 opt-in skips), 68 installed-artifact tests passed, 339 frontend tests and 15 release checks passed, and Pages validation passed. The separate live health smoke passed against real CLI workers/beat and disposable Valkey, covering local-node isolation, broker loss, scheduler freeze/recovery, clean marker removal, and forced-kill detection. Formatting, lint/import contracts, types, pre-commit hooks, and workflow lint passed. Full distributed workloads from the final image and active-task worker shutdown remain outside this health smoke's coverage.
