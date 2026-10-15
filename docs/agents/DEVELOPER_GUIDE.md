# DEVELOPER_GUIDE: Getting Started

This guide walks you through setting up the `camply` development environment.

## 📋 Prerequisites

- **Python 3.12+** (Managed via [uv](https://github.com/astral-sh/uv))
- **Node.js 24+** and **pnpm 10.34.6** (Node 24 is selected by `frontend/.node-version`, CI, and Docker; pnpm is pinned in `frontend/package.json`)
- **Docker & Docker Compose**
- **go-task** (The [Taskfile](https://taskfile.dev) runner)

---

Enable pnpm with `corepack enable` before running frontend tasks. If your Node.js installation does not include Corepack, install it with `npm install --global corepack` first. Corepack reads the pinned pnpm version from `frontend/package.json`.

Frontend installs use `pnpm install --frozen-lockfile`. To change frontend dependencies, run `pnpm add <package>` (or `pnpm add --save-dev <package>`) from `frontend/` and commit both `package.json` and `pnpm-lock.yaml`.

Running `task` without arguments lists available workflows. Use `task install` to install project dependencies.

## Standalone runtime

Docker is optional for this workflow. Run `task standalone:install`, `task standalone:build`, then `task standalone:run -- --port 8000`. The build stages root-based assets into the backend wheel and packages the complete Alembic revision graph in the db wheel. The launcher validates resources, upgrades the configured SQLite file, then serves the UI, `/api`, and local background loops on `127.0.0.1:8000`. `CAMPLY_RUNTIME_MODE` is independent of authentication and deployment environment.

Set `CAMPLY_DB_HOST` to an absolute writable file path to choose storage. On macOS the default is the platform-specific camply application-data directory, not a checkout path. Use **Sync Providers** in Admin Operations for the first catalog import; later refreshes run at midnight UTC. Searches and Pushover delivery need access to their upstream services. Set the existing `PUSHOVER_APP_TOKEN` and configure each user's Pushover key.

For session login over local HTTP, set `CAMPLY_AUTH_MODE=session`, securely inject `CAMPLY_LOGIN_USERNAME`, `CAMPLY_LOGIN_PASSWORD`, and `CAMPLY_SESSION_SECRET`, set `CAMPLY_SESSION_COOKIE_SECURE=false`, and include the exact frontend origin in `CAMPLY_CORS_ORIGINS`. HTTPS deployments retain secure cookies. Auth0 callbacks must use the Python-served origin. Automatic shared-admin login remains the default.

For installation outside the checkout, create a Python 3.12 environment and install all four wheels from `backend/dist` with `uv pip install --python /path/to/venv/bin/python backend/dist/*.whl`. Start with `CAMPLY_RUNTIME_MODE=standalone /path/to/venv/bin/python -m backend.standalone`. No Vite or Node process is needed. To supply a separate prebuilt UI, set `CAMPLY_FRONTEND_DIR` to its absolute directory. Build assets before producing release wheels; normal editable backend installs do not require frontend assets.

Only one process may use a standalone database. The launcher rejects conflicting worker counts and reload settings; use the launcher rather than a multi-worker ASGI command. Local scheduling uses bounded queues with one consumer each for checks, catalog refreshes, and delivery. The API stays asynchronous during upstream requests. SQLite WAL, foreign keys, a one-second busy timeout, short write transactions, and shared lifespan resources support this small-instance workload. Catalog updates retain each provider's existing commit boundaries; a refresh of all providers is not one transaction.

To back up, stop the application before copying its database, or use SQLite's online backup API (for example `sqlite3 /path/to/camply.db '.backup /path/to/backup.db'`). Do not copy only a live database file while its WAL is active. Stop the application, restore a consistent backup to the configured path, and restart; migrations are reapplied idempotently. Pending alerts survive restart, and interrupted sends consume their persisted attempt budget. Upstream acceptance followed by a process failure can cause a duplicate after restart.

Run `task standalone:test` for a clean installed-wheel dependency audit plus real HTTP, SQLite recovery, session/CSRF, and Chromium desktop/mobile checks using synthetic upstreams. It needs the development environment and `task frontend:browser:install`, with no backing service containers. Separately, `task backend:migration:test` validates PostgreSQL upgrades in a disposable Docker container, and `task admin:smoke` covers distributed administration. `task install` and other development checks deliberately install distributed extras; `standalone:install` selects the core-only runtime.

## 🚀 Quick Start (Local Setup)

1.  **Clone & Install**:

    ```bash
    git clone https://github.com/juftin/camply.git
    cd camply
    task install
    ```

2.  **Configure Environment**:
    - Copy `.env.example` to `.env`: `cp .env.example .env`.
    - Adjust any settings as needed (see [docs/CONFIGURATION.md](CONFIGURATION.md)).
    - Choose `CAMPLY_AUTH_MODE=none` (default automatic admin login), `session` (in-app password login), or `auth0`. The choice is independent of `CAMPLY_ENVIRONMENT`; see CONFIGURATION.md for the required settings.

3.  **Start the Stack**:

    ```bash
    # Option A: Backing services in Docker, backend + frontend on host (recommended for active dev)
    task compose:infra     # Starts Postgres (db) and Valkey in background
    task dev               # Starts FastAPI backend (port 8000) and Vite frontend (port 5173) in watch mode

    # Option B: Entire stack in Docker Compose
    task compose:up        # Starts all services (backend, frontend, db, valkey, worker)
    ```

4.  **Access the App**:
    - **Frontend**: `http://localhost:5173` (or over Tailscale at `http://<tailscale-ip>:5173`)
    - **API Docs**: `http://localhost:8000/api/docs`

---

## 🛠️ Common Workflows

### 1. Database Migrations

We use Alembic for backend migrations.

- **Generate**: `task backend:migration -- "your message"`
- **Apply**: `task backend:migration-upgrade`

### 2. Provider Migration

When porting logic from the legacy `cli/` to the new `backend/packages/providers`:

1.  Define the internal Pydantic models in `models/`.
2.  Implement the `BaseProvider` interface.
3.  Add unit tests using `pytest-vcr` to record initial API responses.

### 3. API & Client Generation

If you change a FastAPI router:

1.  Verify the backend types: `task backend:check`.
2.  Update the frontend SDK: `task frontend:codegen`.

---

## 🧪 Testing Discipline

### Backend

- Run all tests: `task backend:test`
- Update VCR cassettes: `task backend:test -- --vcr-record=all`

### Frontend

- Run vitest: `task frontend:test`
- Type check: `task frontend:check`
- Lint and check formatting: `task frontend:lint`
- Fix lint and formatting issues: `task frontend:fix`
- Build static assets: `task frontend:build:static`

The frontend uses Vite 8 (Rolldown), Vitest 5, Oxlint, Oxfmt, and native TypeScript 7. Oxlint preserves the existing ESLint rules, including React Hooks and Fast Refresh; the experimental `no-undef` rule remains enabled. Oxfmt uses an 80-column print width and excludes generated artifacts through the root `.oxfmtrc.json`.

`task frontend:check` and production builds invoke the native compiler installed as `@typescript/native`. The separate `typescript` 5 dependency supplies the JavaScript compiler API required by `openapi-typescript`; it is not used for project checks. Run the native compiler through Task rather than invoking the ambiguous `tsc` executable directly.

### UI Snapshots & Visual Regression

- Run visual snapshots & compare against baselines: `task snapshot`
- Update visual snapshot baselines: `task snapshot:update`
- Verify snapshots match baselines (CI regression check): `task snapshot:check`
- View visual report: `frontend/snapshots/REPORT.md` (markdown) or `frontend/snapshots/report.html` (interactive)
- Run component DOM snapshots: `task frontend:test` (or `task test`)

Visual regression checking is automated in GitHub Actions CI via the `ui-snapshots` workflow job, which installs headless Chromium, executes `task snapshot:check` with deterministic test clocks, and uploads report and visual diff artifacts on completion.

---

## ✅ Pre-Commit & Linting

The project uses `pre-commit` to ensure code quality.

- Run manually: `task pre-commit`
- Auto-fix issues: `task fix`

### API contract verification

Use `task api:generate` to export the local FastAPI OpenAPI schema and regenerate committed TypeScript types without a running backend. Run `task api:check` to verify that the generated file matches the backend. Admin pages consume these generated types directly, so fixtures must use the actual response shapes. The API Contract CI job checks drift on every PR.

### Admin live smoke test

Run `task frontend:browser:install` once if Chromium is unavailable, then `task admin:smoke` with Docker running. This creates test-owned Valkey and Prometheus containers on random loopback ports, a synthetic Celery worker, and an HTTP API backed by the test SQLite database. It cleans up its containers and processes after the test.

The smoke test verifies real failure/retry signal handling, distinct attempts and counter values, worker inspection, Prometheus queries, and Chromium user suspension/restoration and scan pause/resume without intercepted API responses. It also verifies stale inspection after stopping the worker. CI runs this as **Admin Live Smoke**; the normal unit suite skips this opt-in test. External booking providers, notification delivery, PostgreSQL migrations, and prefork deployment behavior are outside this smoke test.
