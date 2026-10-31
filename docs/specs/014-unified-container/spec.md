# Shared camply container

## Requirements

- Publish one application image, `ghcr.io/juftin/camply`, containing Python, Nginx, the complete installed wheel, and all runtime extras.
- Run API, frontend, Celery worker, and beat as separate containers from this image using command overrides. Preserve the API default command.
- Locate bundled frontend assets internally in `camply serve frontend` without importing server dependencies. Report missing bundled assets clearly.
- Configure Nginx to serve that directory directly, preserving SPA fallback, asset caching, health checks, and the API proxy.
- Nginx and informational CLI commands must start without database migrations. The backend launcher owns API migrations and the existing worker/beat skip setting.
- Preserve external PostgreSQL, Valkey, and Prometheus services, application storage, frontend build settings, and release tag/version rules.
- Publish each release under four image tags: the major version (`v1`), full version (`v1.2.3`), seven-character release commit SHA, and `latest`.
- Provide `camply serve frontend`, `camply serve backend`, `camply serve worker`, and `camply serve beat` as foreground process launchers. Keep optional runtime imports out of CLI startup, report missing executables clearly, and forward backend/worker runtime arguments.
- Package both Nginx configurations with the CLI and render the installed static path into a writable per-process runtime directory. Read the API upstream from `CAMPLY_BACKEND_URL`, defaulting to `http://backend:8000` when unset or empty; expose the override through Compose as well.
- Preserve API migrations, worker/beat migration skipping, runtime directory setup, and Compose's initial provider-sync dispatch before beat.
- Bare `camply serve` starts the existing standalone launcher: bundled UI, API, SQLite migrations, and local background work in one process. Support standalone `--host`/`--port` options and require the `server` extra without importing optional runtimes for help or explicit subcommands.
- Validate each Python role's runtime modules in the CLI interpreter before startup or migrations. Launch Gunicorn and Celery with that interpreter so unrelated executables on `PATH` cannot bypass missing extras or select another installation.
- Preserve existing required backend/frontend Docker check names while performing a single shared image build. A failed, cancelled, or skipped shared build must not pass the frontend check.
- Preserve foreground process ownership and native runtime signal handling. Compose must use graceful `SIGQUIT` for Nginx, `SIGTERM` for Python roles, and an explicit shutdown grace period; document that `SIGKILL` cannot perform cleanup and host supervisors must own child process groups.

## Acceptance

Render Compose and publication plans to verify one application image and build configuration across roles. Verify CLI behavior in clean base-package installations, entrypoint dispatch, and real Nginx HTTP responses from the shared runtime. The final image runs as `camply` and contains no Node tooling.
