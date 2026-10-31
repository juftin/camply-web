<div align="center">
<a href="https://github.com/juftin/camply-web">
  <img src="src/frontend/public/branding/camply-horizontal.svg" width="400" alt="camply">
</a>
</div>

**camply**, the campsite finder ⛺️, watches for availability at sold-out campgrounds and notifies you when a matching stay becomes available. It supports a Python/SQLite standalone application and a distributed deployment with PostgreSQL, Celery, and Valkey.

Licensed under [PolyForm Noncommercial 1.0.0](LICENSE).

## Run without backing services

The standalone runtime serves the UI, API, and background polling in one Python process. From a checkout:

```bash
task standalone:install
task standalone:build
task standalone:run
```

Open <http://127.0.0.1:8000>. Use **Sync Providers** in Admin Operations to load the catalog. Configure the Pushover application token and each user's key to receive alerts. The default authentication mode signs in as a shared administrator; select session or Auth0 authentication before sharing an instance. See [configuration](docs/operations/CONFIGURATION.md) and the [standalone guide](docs/development/DEVELOPER_GUIDE.md#standalone-runtime).

An installed `camply[server]` package starts the complete standalone application with `camply serve`. Override the listener with `camply serve --host 0.0.0.0 --port 9000`. Explicit `camply serve frontend`, `backend`, `worker`, and `beat` subcommands run individual roles.

Standalone uses one process on one host, with persisted scans and pending alerts. Historical monitoring charts require the distributed deployment. `task standalone:run` uses `build/frontend` as its default development UI; an explicit `CAMPLY_FRONTEND_DIR` selects another absolute asset directory.

## Build and install the complete application

Checkout builds require Python 3.14, uv, Node 24, and the pnpm version pinned in `package.json`. Python package consumers are supported on Python >=3.11.

```bash
task install
uv run python -m build
```

Using the project's interpreter, `python -m build` also works directly. It creates one `camply` sdist and wheel in `dist/`; `task dist` uses the same complete artifact contract through uv. The build installs frontend dependencies from the frozen lockfile and compiles root-hosted assets with same-origin `/api`. Missing source-build prerequisites fail rather than producing an incomplete wheel.

The sdist contains frontend source and prepared assets. Rebuilding its wheel and installing or running a prepared wheel require no Node or pnpm. Every wheel contains the UI, Python typing markers, Gunicorn configuration, and the full Alembic migration graph. The build does not stage generated assets into working source files.

The shared `camply` Docker image includes Python and Nginx. `camply serve frontend` locates its bundled assets automatically and renders the packaged Nginx configuration at startup. Editable installs without bundled assets report a clear error when serving the frontend.

Install the actual wheel path into a uv-managed environment with the desired extras:

```bash
uv pip install 'dist/camply-0.1.0-py3-none-any.whl[server]'
camply serve
```

Substitute the artifact version and run the installed environment's `camply` executable. Installed standalone applications use package-owned assets by default. `CAMPLY_FRONTEND_DIR` remains an optional absolute override. SQLite storage defaults to the platform's camply application-data directory; set `CAMPLY_DB_HOST` to an absolute writable path to choose another location.

| Installation          | Capabilities                                                                                        |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| `camply`              | Provider APIs, SQLite persistence, migrations, `camply --version`/`--help`, and `populate-database` |
| `camply[server]`      | FastAPI and standalone HTTP application                                                             |
| `camply[distributed]` | Celery worker/beat and Redis client                                                                 |
| `camply[postgres]`    | PostgreSQL driver                                                                                   |
| `camply[sentry]`      | Optional error reporting                                                                            |

Extras select dependencies; all installations receive the same application files. The existing full stack selects `server,distributed,postgres,sentry`. API-only serving does not start scheduled scans unless standalone mode is selected.

## Develop from the repository root

```bash
task install
task compose:infra
task dev
```

Vite serves development UI on port 5173 and proxies `/api` to the backend on port 8000. Use `task compose:up` to run the whole distributed stack in containers. One root Dockerfile builds `ghcr.io/juftin/camply` for the API, Nginx, Celery worker, and beat; root Compose defines all services and preserves named volumes and `.data/camply` storage.

Build the shared image with `task build`. The default command is `camply serve backend`; Compose selects the other roles with command overrides:

| Role       | Command in the `camply` image    |
| ---------- | -------------------------------- |
| Standalone | `camply serve`                   |
| API        | `camply serve backend` (default) |
| Frontend   | `camply serve frontend`          |
| Worker     | `camply serve worker`            |
| Scheduler  | `camply serve beat`              |

`camply serve backend` applies database migrations unless `SKIP_MIGRATIONS=1`; frontend and worker commands do not migrate. Compose waits for the backend's post-migration health check before starting workers or beat. Its scheduler runs `camply serve beat --sync-providers` to enqueue the initial catalog sync before starting beat. Bare `camply serve beat` does not enqueue a startup sync; the option preserves the task's ten-minute expiry and exits on dispatch failure. Set `CAMPLY_VERSION` to select the image tag in Compose. PostgreSQL, Valkey, and Prometheus keep their upstream images.

Outside Docker, standalone and backend serving require `camply[server]`, and worker/beat require `camply[distributed]`. The frontend requires system Nginx and a prepared wheel with built assets. Launchers check dependencies before startup and use the CLI's Python environment. Help remains available with only the base package installed.

Serving commands replace the CLI process with the foreground runtime, preserving direct signal delivery. Compose sends `SIGTERM` to Python roles and `SIGQUIT` to Nginx, with one minute to stop before a forced kill. For Nginx outside Compose, use `docker run --stop-signal SIGQUIT --stop-timeout 60` or send `SIGQUIT` directly. See [shutdown behavior](docs/operations/CONFIGURATION.md#process-shutdown) for forced termination and host process groups.

Backend and worker commands forward extra arguments to Gunicorn or Celery, for example `camply serve backend --bind 127.0.0.1:9000`, `camply serve worker --concurrency=2`, or `camply serve beat --schedule /tmp/camply-beat`. Backend serving requires `camply[server]`; worker commands require `camply[distributed]`. Each command replaces itself with the runtime process so container signals reach it directly.

Frontend serving requires system Nginx with `/etc/nginx/mime.types`, as installed in the image. Set `CAMPLY_BACKEND_URL` to choose the API upstream; it defaults to `http://backend:8000`. For example, `CAMPLY_BACKEND_URL=http://api.internal:9000 camply serve frontend` proxies `/api/` to that server. Compose forwards the same variable. Use an origin without a trailing slash to preserve the `/api/` path. The frontend listens on port 8080, renders the two package-owned templates under a writable temporary directory, and runs Nginx in the foreground without modifying `/etc/nginx`. Nginx config resources live in `src/camply/cli/nginx/`.

```text
/
├── pyproject.toml, uv.lock, package.json, pnpm-lock.yaml
├── Taskfile.yaml, tasks/{python,frontend}.yaml
├── Dockerfile, docker-compose.yaml, docker-bake.release.hcl
├── src/
│   ├── camply/{cli,db,providers,server,worker}/
│   └── frontend/
│       ├── components/, hooks/, lib/, pages/, public/, test/
│       ├── functions/, tooling/
│       └── wrangler.jsonc
├── tests/                    # Python, packaging/release, and visual baselines
├── deploy/                   # Entrypoint and Prometheus configuration
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

These local commands need no Cloudflare authentication. The API proxy needs an externally supplied `CAMPLY_API_ORIGIN`; see [Pages configuration and operator migration](docs/operations/CONFIGURATION.md#cloudflare-pages-frontend) for production/preview bindings and hosted build-root settings. No deployment is performed by tests.

See the [developer guide](docs/development/DEVELOPER_GUIDE.md), [architecture](docs/architecture/ARCHITECTURE_DEEP_DIVE.md), [release operations](docs/operations/RELEASES.md), and [feature 013](docs/specs/013-root-project-layout/plan.md).
