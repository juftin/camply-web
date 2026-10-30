# Implementation plan

1. Locate bundled assets from the CLI's package path, checking for `index.html`; verify absolute, shell-friendly output and clean base installations.
2. Retain the shared wheel build, install Nginx alongside Python in one final `camply` stage, and render Nginx's root from the installed CLI output with restricted `envsubst` substitution.
3. Reuse the same Compose image/build configuration for API, frontend, worker, and beat. Dispatch Nginx and CLI before migration setup; keep Gunicorn as the default.
4. Build and publish one image through the existing Compose backend Bake target, preserving task namespaces and release aliases; consolidate Docker CI into one job.
5. Verify role dispatch, release plans, lint/types, installed artifacts, and container HTTP behavior; update current deployment documentation and the global checklist.

## Constitution check

The change keeps root manifests, the complete-wheel packaging contract, internal dependency boundaries, the non-root runtime, and Task entrypoints. It adds no Python dependencies or application process supervisor. Each distributed service remains independently managed by Compose.
