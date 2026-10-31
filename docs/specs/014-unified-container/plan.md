# Implementation plan

1. Locate bundled assets internally from the CLI's package path, checking for `index.html`; verify absolute paths in rendered Nginx configuration and clean base installations.
2. Retain the shared wheel build, install Nginx alongside Python in one final `camply` stage, and render package-owned Nginx templates at runtime using the installed static root.
3. Reuse the same Compose image/build configuration for API, frontend, worker, and beat. Let the backend launcher own API migrations, keep frontend/worker startup independent, and use `camply serve backend` as the default.
4. Build and publish one image through the existing Compose backend Bake target, preserving task namespaces and release aliases. Build once in CI and retain both required Docker check names; the frontend check must fail unless the shared image build succeeded.
5. Verify role dispatch, release plans, lint/types, installed artifacts, and container HTTP behavior; update current deployment documentation and the global checklist.

## Constitution check

The change keeps root manifests, the complete-wheel packaging contract, internal dependency boundaries, the non-root runtime, and Task entrypoints. It adds no Python dependencies or application process supervisor. Each distributed service remains independently managed by Compose.

## Role launchers

1. Add behavior tests for all four launchers, missing dependencies, argument forwarding, migration ownership, and packaged Nginx resources.
2. Move Nginx templates into `camply/cli/nginx`; render only explicit path placeholders and use a writable Nginx prefix without modifying system configuration.
3. Launch Gunicorn, Nginx, and Celery with process replacement. The backend command applies migrations unless skipped; the shell entrypoint retains container directory preparation and raw-command compatibility.
4. Switch Docker/Compose to the CLI commands, remove build-time Nginx rendering and gettext, and preserve Compose's provider synchronization before beat.
5. Verify unit and installed-artifact behavior, real container roles and shutdown, then update the existing PR.

## Default standalone serving

Invoke the installed `camply.server.standalone` module with the current Python interpreter when `camply serve` has no subcommand. Forward standalone listener options, select standalone mode before process replacement, and retain the existing launcher's resource validation, migrations, and single-process scheduling. Explicit role subcommands and the distributed Docker/Compose default remain unchanged. Route the development standalone task through the CLI and verify bare invocation, missing extras, listener options, help, and real installed standalone HTTP behavior.

## Runtime dependency checks

Check required modules using `importlib.util.find_spec` without importing optional runtimes. Share common server checks across standalone/backend and add Gunicorn-specific checks only for backend serving. Require Celery, Redis, and metrics modules for worker/beat. Replace the process with the current interpreter's `-m gunicorn` or `-m celery`; retain `PATH` lookup only for system Nginx. Verify partial extras fail before migrations, unrelated executables cannot bypass checks, and an installed backend launcher works with an empty `PATH`.

## Shutdown behavior

Retain process replacement and native signal handlers. Configure Compose to send `SIGQUIT` to Nginx and `SIGTERM` to Python roles, allowing one minute before forced termination. Verify live installed standalone/Gunicorn cleanup after `SIGTERM`, unchanged standalone PID ownership, direct `SIGKILL` termination, and SQLite integrity after termination. Document host process-group supervision and the limits of cleanup after forced kills.

## Downstream API upstream

Read `CAMPLY_BACKEND_URL` in the frontend launcher, defaulting to `http://backend:8000` when unset or empty. Render only its explicit template placeholder as a quoted Nginx value, preserving existing proxy variables/settings. Forward the override through Compose, verify default/custom URLs in CLI and isolated installations, and check real Nginx proxy routing with a synthetic upstream. Document native `proxy_pass` URI semantics.

## Distributed startup ordering and initial sync

Compose workers and beat must wait for the backend health check, which only becomes available
after its migration step. Verify dependency rendering to prevent processing against an old or
empty schema. Add an opt-in `camply serve beat --sync-providers` option that dispatches the existing
catalog task with a ten-minute expiry through the CLI interpreter before process replacement.
Keep default beat startup free of dispatch, native argument forwarding, base-only help, and
optional dependency checks. A failed dispatch must stop startup. Cover these contracts with CLI,
entrypoint, clean-installation, and release regressions; verify fresh-database startup ordering.
