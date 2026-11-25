# Runtime and Packaging Reference

Technical reference for Python package extras, `camply serve` / `camply db` subcommands, distribution builds, and Nginx/Pages integration. For self-hosting setup, see [Self-Hosting](../self-hosting/index.md).

## Standalone runtime contract

`camply serve` runs the UI, API, and local background loops in one Python process backed by SQLite. Override the listener with `camply serve --host 0.0.0.0 --port 9000`; explicit `camply serve frontend`, `backend`, `worker`, and `beat` subcommands run individual roles.

For checkout testing, `task standalone:install`, `task standalone:build`, and `task standalone:run` default `CAMPLY_FRONTEND_DIR` to root `build/frontend`. See [Standalone hosting](../self-hosting/standalone.md) for end-user installation and [Configuration](CONFIGURATION.md) for runtime environment variables.

## Destination photos and practical details

Provider catalog syncs also refresh cached photos and practical information for Recreation.gov, the ten supported UseDirect park systems, and ReserveAmerica. Both **Sync Providers** and scheduled ingestion use this workflow. To refresh a provider from the CLI after upgrading the schema:

```bash
camply db migrate
camply db metadata --provider-id 1
```

Use `--provider-id all` to refresh all registered provider catalogs. Each CLI invocation enriches at most 100 stale destinations per provider. Without a background runtime, repeat the command to continue the backlog.

Both worker runtimes discover due enrichment independently of daily catalog imports. Distributed beat dispatches `catalog.enrich_all` each heartbeat (normally five minutes); each `catalog.enrich_provider` task handles at most 100 destinations and queues a short-delayed continuation when successful work remains. Standalone mode starts its own supervised enrichment consumer and yields between passes. This automatically backfills existing destinations after deployment, including records beyond the first batch, without repeatedly downloading/importing entire catalogs. Update/restart both the worker and beat roles when deploying this behavior.

Successful details remain fresh for seven days; unsuccessful attempts retain prior content and have a one-hour retry cooldown. Whole-batch failures stop immediate continuation and periodic discovery resumes later. Catalog updates can succeed even when optional enrichment is unavailable. Photos can remain absent until their destination's background batch finishes; the absence of source photos is also a valid result. Check `catalog.enrich_provider` task outcomes and enrichment warnings when diagnosing missing content.

Photos stay on upstream hosts, and coverage varies by destination. Detail pages display available captions/credits, source links, and the last successful update. Missing or broken images do not block descriptions, maps, booking links, or monitoring. Page reads and availability scans never perform enrichment requests. GoingToCamp media, official-site scraping, and dated UseDirect narrative harvesting remain outside this release.

## Build and install the complete application

Checkout builds require Python 3.14, uv, Node 24, and the pnpm version pinned in `package.json`. Python package consumers are supported on Python >=3.11.

```bash
task install
uv run python -m build
```

Using the project's interpreter, `python -m build` also works directly. It creates one `camply` sdist and wheel in `dist/`; `task dist` uses the same complete artifact contract through uv. The build installs frontend dependencies from the frozen lockfile and compiles root-hosted assets with same-origin `/api`. Missing source-build prerequisites fail rather than producing an incomplete wheel.

The sdist contains frontend source and prepared assets. Rebuilding its wheel and installing or running a prepared wheel require no Node or pnpm. Every wheel contains the UI, Python typing markers, Gunicorn configuration, and the full Alembic migration graph. The build does not stage generated assets into working source files.

The shared `camply-web` Docker image includes Python and Nginx. `camply serve frontend` locates its bundled assets automatically and renders the packaged Nginx configuration at startup. Editable installs without bundled assets report a clear error when serving the frontend.

Install the actual wheel path into a uv-managed environment with the desired extras:

```bash
uv pip install 'dist/camply_web-0.1.0-py3-none-any.whl[server]'
camply serve
```

Substitute the artifact version and run the installed environment's `camply` executable. Installed standalone applications use package-owned assets by default. `CAMPLY_FRONTEND_DIR` remains an optional absolute override. SQLite storage defaults to the platform's camply application-data directory; set `CAMPLY_DB_HOST` to an absolute writable path to choose another location.

| Installation              | Capabilities                                                                                                                                                |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `camply-web`              | Provider discovery and foreground availability CLI, SQLite persistence, migrations, help/version, and `camply db` (`info`, `migrate`, `delete`, `metadata`) |
| `camply-web[server]`      | FastAPI and standalone HTTP application                                                                                                                     |
| `camply-web[distributed]` | Celery worker/beat and Redis client                                                                                                                         |
| `camply-web[postgres]`    | PostgreSQL driver                                                                                                                                           |
| `camply-web[sentry]`      | Optional error reporting                                                                                                                                    |

Extras select dependencies; all installations receive the same application files. The existing full stack selects `server,distributed,postgres,sentry`. API-only serving does not start scheduled scans unless standalone mode is selected.

For local provider discovery and terminal availability monitoring, use the
[command-line guide](../cli.md). These workflows use live provider APIs directly
without a database, catalog import, account or optional runtime extra.

## Kubernetes

Deploy the distributed stack with the [Helm chart](https://github.com/juftin/camply-web/blob/main/deploy/helm/README.md).
It includes migration startup gates, optional PostgreSQL/Valkey/Prometheus,
Ingress or Gateway API routing, and configurable PVCs or external services.

## Develop from the repository root

```bash
task install
task compose:infra
task dev
```

Vite serves development UI on port 5173 and proxies `/api` to the backend on port 8000. Use `task compose:up` to run the whole distributed stack in containers. One root Dockerfile builds `ghcr.io/juftin/camply-web` for the API, Nginx, Celery worker, and beat; root `docker-compose.yaml` builds and runs the local development stack (preserving named volumes and `.data/camply` storage), while `deploy/compose/` provides self-contained GHCR-pulling stacks (`docker-compose.yaml` for distributed quick start, `docker-compose.standalone.yaml` for single-container SQLite, and `docker-compose.production.yaml` for hardened production). See [Docker & Kubernetes](../self-hosting/containers.md).

Build the shared image with `task build`. The default command is `camply serve backend`; Compose selects the other roles with command overrides:

| Role       | Command in the `camply-web` image |
| ---------- | --------------------------------- |
| Standalone | `camply serve`                    |
| API        | `camply serve backend` (default)  |
| Frontend   | `camply serve frontend`           |
| Worker     | `camply serve worker`             |
| Scheduler  | `camply serve beat`               |

`camply serve backend` applies database migrations unless `SKIP_MIGRATIONS=1`; frontend and worker commands do not migrate. Compose waits for the backend's post-migration health check before starting workers or beat. Its scheduler runs `camply serve beat --sync-providers` to enqueue the initial catalog sync before starting beat. Bare `camply serve beat` does not enqueue a startup sync; the option preserves the task's ten-minute expiry and exits on dispatch failure. Set `CAMPLY_VERSION` to select the image tag in Compose. PostgreSQL, Valkey, and Prometheus keep their upstream images.

Outside Docker, standalone and backend serving require `camply-web[server]`, and worker/beat require `camply-web[distributed]`. The frontend requires system Nginx and a prepared wheel with built assets. Launchers check dependencies before startup and use the CLI's Python environment. Help remains available with only the base package installed.

Serving commands replace the CLI process with the foreground runtime, preserving direct signal delivery. Compose sends `SIGTERM` to Python roles and `SIGQUIT` to Nginx, with one minute to stop before a forced kill. For Nginx outside Compose, use `docker run --stop-signal SIGQUIT --stop-timeout 60` or send `SIGQUIT` directly. See [shutdown behavior](../operations/CONFIGURATION.md#process-shutdown) for forced termination and host process groups.

Backend and worker commands forward extra arguments to Gunicorn or Celery, for example `camply serve backend --bind 127.0.0.1:9000`, `camply serve worker --concurrency=2`, or `camply serve beat --schedule /tmp/camply-beat`. Backend serving requires `camply-web[server]`; worker commands require `camply-web[distributed]`. Each command replaces itself with the runtime process so container signals reach it directly.

Frontend serving requires system Nginx with `/etc/nginx/mime.types`, as installed in the image. Set `CAMPLY_BACKEND_URL` to choose the API upstream; it defaults to `http://backend:8000`. For example, `CAMPLY_BACKEND_URL=http://api.internal:9000 camply serve frontend` proxies `/api/` to that server. Compose forwards the same variable. Use an origin without a trailing slash to preserve the `/api/` path. The frontend listens on port 8080, renders the two package-owned templates under a writable temporary directory, and runs Nginx in the foreground without modifying `/etc/nginx`. Nginx config resources live in `src/camply/cli/nginx/`.

Health probes follow the same roles: `camply serve healthcheck` checks standalone, and `camply serve healthcheck backend`, `frontend`, `worker`, or `beat` checks that service. They print `healthy` and exit 0 on success, or exit 1 with a diagnostic. Compose uses these commands for all four application services. HTTP probes accept `--url` and `--timeout`; the worker probe targets the local Celery node through Valkey, and beat checks a scheduler-loop heartbeat. See [healthcheck configuration](../operations/CONFIGURATION.md#service-health-checks) for probe semantics and overrides. Run `task backend:healthcheck:test` to verify real worker and beat probes with a disposable Valkey container.

```text
/
├── pyproject.toml, uv.lock, package.json, pnpm-lock.yaml
├── Taskfile.yaml, tasks/{python,frontend}.yaml
├── Dockerfile, docker-compose.yaml
├── src/
│   ├── camply/{cli,db,providers,server,worker}/
│   └── frontend/
│       ├── components/, hooks/, lib/, pages/, public/, test/
│       ├── functions/, tooling/
│       └── wrangler.jsonc
├── tests/                    # Python, packaging/release, and visual baselines
├── deploy/                   # Compose flavors, entrypoint, Helm chart, and Prometheus configuration
└── docs/
    ├── development/, architecture/, operations/
    └── specs/                # Feature specifications and implementation plans
```

Run `task` to list workflows. Existing `backend:*` and `frontend:*` namespaces execute from the root. Editable Python installs and Python-only checks do not require JavaScript tooling. Generated frontend builds and API schemas live under `build/`, release archives under `dist/`, and reports/screenshots under `tmp/`.

```bash
task fix
task lint
task check
task test
task api:check
```

The frontend uses React, TypeScript, Vite, Tailwind, Shadcn/UI, and MapLibre. Component tests stay colocated; approved screenshot baselines live in `tests/frontend/snapshots/baselines`. Python uses FastAPI, SQLAlchemy/Alembic, shared async provider/polling logic, and optional distributed adapters. Import Linter protects component and optional-dependency boundaries.

## Cloudflare Pages

`src/frontend/wrangler.jsonc` defines the existing Pages project, output path, and compatibility date. Functions and frontend tooling live beside it; root Tasks select the nested Pages directory:

```bash
task frontend:pages:check
task frontend:pages:dev
```

These local commands need no Cloudflare authentication. The API proxy needs an externally supplied `CAMPLY_API_ORIGIN`; see [Pages configuration and operator migration](../operations/CONFIGURATION.md#cloudflare-pages-frontend) for production/preview bindings and hosted build-root settings. No deployment is performed by tests.

See the [developer guide](../development/DEVELOPER_GUIDE.md), [architecture](../architecture/ARCHITECTURE_DEEP_DIVE.md), [release operations](../operations/RELEASES.md), and [feature 013](../specs/019-root-project-layout/plan.md).
