# Developer Guide

All project workflows run through [go-task](https://taskfile.dev/) (`Taskfile.yaml`) from the repository root. Run `task` with no arguments to list available tasks.

## Prerequisites

- **Python >= 3.11** (development and primary CI default to 3.14) managed by [uv](https://docs.astral.sh/uv/)
- **Node.js >= 24** and **pnpm 12.15.0** (enable with `corepack enable`)
- **Docker & Docker Compose** (for PostgreSQL, Valkey, and container smoke tests)
- **go-task** and **GitHub CLI (`gh`)**

## Local setup

Clone the repository, install dependencies, and verify your toolchain:

```bash
git clone https://github.com/juftin/camply-web.git
cd camply-web
task install
task doctor
```

Copy the example environment file and start the stack:

```bash
cp docs/examples/.env.example .env
task compose:infra    # PostgreSQL and Valkey in Docker
task dev              # FastAPI (port 8000) and Vite (port 5173)
```

By default `.env` leaves SQLite active. Uncomment the `CAMPLY_DB_*` PostgreSQL block in `.env` if you want to develop against the Compose database. To run distributed Celery workers locally alongside `task dev`, run `UV_ENV_FILE=.env task backend:worker:all` in another terminal.

To develop against the standalone SQLite runtime from your checkout:

```bash
task standalone:install
task standalone:build
task standalone:run -- --port 8000
```

## Quality checks and tests

Run these checks before opening a pull request:

```bash
task fix              # Auto-format and auto-fix Ruff + Oxlint/Oxfmt
task check            # Format, lint (Ruff, Oxlint, Import Linter), and type check (MyPy, native tsc)
task test             # Full backend, packaging, frontend, and Pages checks
```

Common targeted test commands:

| Command                                 | Purpose                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| `task backend:test`                     | Python unit and VCR integration tests (`pytest`)                                |
| `task backend:imports`                  | Enforce internal package layer boundaries                                       |
| `task backend:packaging:test`           | Verify isolated wheel and sdist builds (`PACKAGING_PYTHON=3.11` for min Python) |
| `task frontend:test`                    | React/Vitest component and hook tests                                           |
| `task snapshot` / `task snapshot:check` | Capture and compare Playwright UI visual snapshots                              |
| `task standalone:test`                  | End-to-end standalone wheel, SQLite recovery, and browser check                 |

Opt-in Docker integration suites (`task admin:smoke`, `task search:smoke`, `task maps:verify`) run isolated PostgreSQL/Valkey/Chromium checks and require `task frontend:browser:install`.

## Common workflows

- **Database migrations:** Generate with `task backend:migration -- "message"` and apply with `task backend:migration-upgrade`.
- **API client codegen:** After changing FastAPI routes or schemas, run `task api:generate` (and `task api:check` to verify no OpenAPI drift).
- **Provider availability cassettes:** Find confirmed open dates, record a single search, and verify it offline using the [cassette refresh guide](PROVIDER_CASSETTES.md).
- **Standalone wheels/sdists:** Build complete distributions into `dist/` with `uv run python -m build` (or `task dist`). See [Runtime & Packaging](../operations/RUNNING.md) for the packaging contract.

## Working on the docs

The documentation site uses VitePress under `docs/`. Preview live changes on <http://127.0.0.1:8001> without starting the app stack:

```bash
task docs:install
task docs:serve
```

Run `task docs:build` to render `build/docs/`, or `task docs:check` to build and verify all rendered links, navigation rules, and publishing config.

Every production frontend build compiles the VitePress site into `docs/` inside the static bundle (served at `/docs/` from standalone Python, Nginx, and Cloudflare Pages). Successful pushes to `main` also publish a mirror to GitHub Pages (`https://juftin.com/camply-web/`).

## Capacitor mobile client

The [mobile development guide](MOBILE.md) covers bundling the React app for Android and iOS, configuring the hosted API, and running native builds.

## Spec-Kit feature workflows

Feature specifications, plans, and task lists live under `docs/specs/NNN-feature-name/` while `.specify/` remains at the repository root. After updating Spec-Kit scaffolding, run `uv run pytest tests/test_specify_workflows.py`.
