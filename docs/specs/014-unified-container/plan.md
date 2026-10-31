# Implementation plan

1. Locate bundled assets from the CLI's package path, checking for `index.html`; verify absolute, shell-friendly output and clean base installations.
2. Retain the shared wheel build, install Nginx alongside Python in one final `camply` stage, and render package-owned Nginx templates at runtime using the installed static root.
3. Reuse the same Compose image/build configuration for API, frontend, worker, and beat. Let the backend launcher own API migrations, keep frontend/worker startup independent, and use `camply serve backend` as the default.
4. Build and publish one image through the existing Compose backend Bake target, preserving task namespaces and release aliases; consolidate Docker CI into one job.
5. Verify role dispatch, release plans, lint/types, installed artifacts, and container HTTP behavior; update current deployment documentation and the global checklist.

## Constitution check

The change keeps root manifests, the complete-wheel packaging contract, internal dependency boundaries, the non-root runtime, and Task entrypoints. It adds no Python dependencies or application process supervisor. Each distributed service remains independently managed by Compose.

## Role launchers

1. Add behavior tests for all four launchers, missing dependencies, argument forwarding, migration ownership, and packaged Nginx resources.
2. Move Nginx templates into `camply/cli/nginx`; render only explicit path placeholders and use a writable Nginx prefix without modifying system configuration.
3. Launch Gunicorn, Nginx, and Celery with process replacement. The backend command applies migrations unless skipped; the shell entrypoint retains container directory preparation and raw-command compatibility.
4. Switch Docker/Compose to the CLI commands, remove build-time Nginx rendering and gettext, and preserve Compose's provider synchronization before beat.
5. Verify unit and installed-artifact behavior, real container roles and shutdown, then update the existing PR.
