# Contract: Containers, Gunicorn, and Cloudflare Pages

## Container definitions

One root Dockerfile supplies shared application-build stages and final `backend` and `frontend` targets. Root Compose references those targets with root context. Bake retains its existing backend/frontend identities and image-tagging overlay.

Preserve existing API, frontend, Celery worker/beat, PostgreSQL, Valkey, and Prometheus service identities; startup dependencies; health checks; ports; runtime configuration; non-root application users; named volumes `db_data`, `valkey_data`, and `prometheus_data`; and `.data/camply` host storage. Infrastructure file paths change to `deploy`. Frontend build arguments retain community/map settings and same-origin API behavior. Runtime images contain no Node/pnpm or frontend development installation.

Render configuration with explicit synthetic environment settings and without reading secret files. Normalize before/after outputs and compare service/storage semantics, allowing expected Docker context/target and infrastructure-source-path changes. Existing publication tests must check shared root context and distinct targets instead of asserting contexts end with separate project directory names.

## Installed Gunicorn

Use this same invocation in root Tasks and the backend container:

```bash
gunicorn --config python:camply.server.gunicorn camply.server.app:app
```

Preserve current environment-driven settings and platform markers. Validate installed configuration using `--check-config` outside the checkout on a supported platform. Standalone continues to use its existing one-worker launcher independently.

## Wrangler configuration

Implementation creates `src/frontend/wrangler.jsonc` with this baseline:

```jsonc
{
  "$schema": "../../node_modules/wrangler/config-schema.json",
  "name": "camply-81r",
  "pages_build_output_dir": "../../build/frontend",
  "compatibility_date": "2024-11-11",
}
```

The project name matches the existing documented Pages identity and backend origin-trust policy. The compatibility date preserves the existing documented `cache: "no-store"` requirement. Node compatibility flags are unnecessary for the existing web-standard proxy.

Add Wrangler as a pinned root development dependency through pnpm. Root Tasks run the installed executable with `--cwd src/frontend`, so `functions/api/[[path]].ts` is discoverable beside its config and the output/schema paths resolve against the config directory.

| Root task              | Behavior                                                                                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `frontend:pages:check` | Build root-hosted frontend, bundle nested Functions into ignored `tmp/pages-functions`, validate resolved config/routes, and run the local HTTP fixture. No login or external publication. |
| `frontend:pages:dev`   | Build assets, then run local `wrangler pages dev` with the nested project working directory. No production service changes.                                                                |

Direct local command shapes after root dependency installation:

```bash
pnpm exec wrangler --cwd src/frontend pages functions build --outdir ../../tmp/pages-functions
pnpm exec wrangler --cwd src/frontend pages dev
```

Wrangler state is ignored, including nested `.wrangler` directories. Use test-owned fixtures to avoid loading developer secret files during automated checks.

## Environment and hosting migration

- Preserve production and preview `CAMPLY_API_ORIGIN` as externally supplied HTTPS origin bindings. Do not infer the real backend from an example or check in credentials.
- Before eventual publication, account for existing per-environment bindings when adopting file-based configuration; local validation must not modify hosted settings. If an origin is supplied as a protected binding, retain that binding through the operator workflow.
- Root frontend builds use same-origin `/api`. `src/frontend/public/_routes.json` is copied into `build/frontend`, invoking the Function only for `/api` and `/api/*`.
- Git-integrated Pages uses project root `src/frontend`, a build command that invokes the root frozen install/build, and the output from the nested Wrangler config. Set Node/pnpm versions explicitly in Pages build settings to match root pins.
- Wrangler does not replace every Pages dashboard setting. Document the root/build-command migration and binding preservation; do not claim a checked-in file updates the hosted project automatically.

Preserve all current proxy behavior: forwarding request body/headers/cookies, both session/CSRF response cookies, same-origin upstream redirect rewriting, uncached API responses, 503 for invalid/missing backend configuration, and 502 for upstream transport failure. Backend origin trust remains project-scoped, including existing preview/branch origins.

## Verification boundaries

Local config resolution, Function bundling, synthetic HTTP requests, cookie/redirect assertions, container builds, and Bake plans are automated acceptance evidence. Hosted Pages settings, GHCR publication, and externally reachable deployments are separate operator actions; this refactor's tests do not publish or send notifications.
