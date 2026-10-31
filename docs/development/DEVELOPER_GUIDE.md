# DEVELOPER_GUIDE: Getting Started

This guide walks you through setting up the `camply` development environment.

## 📋 Prerequisites

- **Python 3.14** (package supports Python >=3.11; compatibility is tested explicitly) (Managed via [uv](https://github.com/astral-sh/uv))
- **Node.js 24+** and **pnpm 12.15.0** (Node 24 is specified by `package.json` engines, CI, and Docker; pnpm is pinned in `package.json`)
- **Docker & Docker Compose**
- **go-task** (The [Taskfile](https://taskfile.dev) runner)

---

Enable pnpm with `corepack enable` before running frontend tasks. If your Node.js installation does not include Corepack, install it with `npm install --global corepack` first. Corepack reads the pinned pnpm version from `package.json`.

Frontend installs use `pnpm install --frozen-lockfile`. To change frontend dependencies, run `pnpm add <package>` (or `pnpm add --save-dev <package>`) from the repository root and commit both `package.json` and `pnpm-lock.yaml`.

Running `task` without arguments lists available workflows. Use `task install` to install project dependencies.

## Python package capabilities

The backend is one `camply` distribution with internal `server`, `db`,
`providers`, and `worker` subpackages. Development sync installs all extras;
consumers can select `server`, `distributed`, `postgres`, and `sentry`
independently. Base provides providers, SQLite, the `camply` command, and
`populate-database`.
See [backend installation](../../README.md) for artifact examples.

API-only installs do not run scheduled scans: workers, beat, and Valkey/Redis
remain required unless using the standalone runtime. The `camply` CLI (`camply.cli`) is an entrypoint with
`--version`, `--help`, `frontend dir` (the absolute path to bundled static assets), and `frontend serve`/`backend serve`/`worker serve`/`worker beat` role launchers; every prepared distribution includes the frontend, while extras select runtime dependencies. The shared `camply` Docker image includes Python and Nginx, and `camply frontend serve` renders the package-owned Nginx configuration with the installed static root in a writable runtime directory. Compose uses this image for the API, frontend, worker, and beat, selecting each role by command. Import paths
have moved from `backend.*`, `db.*`, `providers.*`, and `worker.*` to
`camply.server.*`, `camply.db.*`, `camply.providers.*`, and `camply.worker.*`.

## Standalone runtime

Docker is optional for this workflow. Run `task standalone:install`, `task standalone:build`, then `task standalone:run -- --port 8000`. The build maps root-hosted assets into the distribution without modifying Python source, and packages the complete Alembic revision graph. The development task defaults `CAMPLY_FRONTEND_DIR` to root `build/frontend`, preserving an explicit override. The installed launcher defaults to package-owned assets, validates resources, upgrades SQLite, then serves the UI, `/api`, and local background loops on `127.0.0.1:8000`. `CAMPLY_RUNTIME_MODE` is independent of authentication and deployment environment.

Set `CAMPLY_DB_HOST` to an absolute writable file path to choose storage. On macOS the default is the platform-specific camply application-data directory, not a checkout path. Use **Sync Providers** in Admin Operations for the first catalog import; later refreshes run at midnight UTC. Searches and Pushover delivery need access to their upstream services. Set the existing `PUSHOVER_APP_TOKEN` and configure each user's Pushover key.

For session login over local HTTP, set `CAMPLY_AUTH_MODE=session`, securely inject `CAMPLY_LOGIN_USERNAME`, `CAMPLY_LOGIN_PASSWORD`, and `CAMPLY_SESSION_SECRET`, set `CAMPLY_SESSION_COOKIE_SECURE=false`, and include the exact frontend origin in `CAMPLY_CORS_ORIGINS`. HTTPS deployments retain secure cookies. Auth0 callbacks must use the Python-served origin. Automatic shared-admin login remains the default.

For installation outside the checkout, install the `camply` package with the `server` extra. Start with `CAMPLY_RUNTIME_MODE=standalone python -m camply.server.standalone`. No Vite or Node process is needed. To supply a separate prebuilt UI, set `CAMPLY_FRONTEND_DIR` to its absolute directory. Build assets before producing release wheels; normal editable backend installs do not require frontend assets.

Alerts use the existing summary/direct modes. Standalone summary links default to the listener origin; set `CAMPLY_APP_URL` to the public URL (including any path prefix) behind HTTPS or a reverse proxy. Site details and map/search APIs use the shared SQLite-backed catalog and latest scan results.

Only one process may use a standalone database. The launcher rejects conflicting worker counts and reload settings; use the launcher rather than a multi-worker ASGI command. Local scheduling uses bounded queues with one consumer each for checks, catalog refreshes, and delivery. The API stays asynchronous during upstream requests. SQLite WAL, foreign keys, a one-second busy timeout, short write transactions, and shared lifespan resources support this small-instance workload. Catalog updates retain each provider's existing commit boundaries; a refresh of all providers is not one transaction.

To back up, stop the application before copying its database, or use SQLite's online backup API (for example `sqlite3 /path/to/camply.db '.backup /path/to/backup.db'`). Do not copy only a live database file while its WAL is active. Stop the application, restore a consistent backup to the configured path, and restart; migrations are reapplied idempotently. Pending alerts survive restart, and interrupted sends consume their persisted attempt budget. The merge migration supports both current-main databases and the earlier standalone PR schema without rewriting its original revision. Upstream acceptance followed by a process failure can cause a duplicate after restart.

Run `task standalone:test` for a clean installed-wheel dependency audit plus real HTTP, SQLite recovery, session/CSRF, and Chromium desktop/mobile checks using synthetic upstreams. It needs the development environment and `task frontend:browser:install`, with no backing service containers. Separately, `task backend:migration:test` validates PostgreSQL upgrades in a disposable Docker container, and `task admin:smoke` covers distributed administration. `task install` and other development checks deliberately install distributed extras; `standalone:install` selects the core-only runtime.

## 🚀 Quick Start (Local Setup)

1.  **Clone & Install**:

    ```bash
    git clone https://github.com/juftin/camply-web.git
    cd camply-web
    task install
    ```

2.  **Configure Environment**:
    - Copy `.env.example` to `.env`: `cp docs/examples/.env.example .env`.
    - Adjust any settings as needed (see [docs/CONFIGURATION.md](../operations/CONFIGURATION.md)).
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

When porting provider logic into `src/camply/providers`:

1.  Define the internal Pydantic models in `models/`.
2.  Implement the `BaseProvider` interface.
3.  Add unit tests using `pytest-vcr` to record initial API responses.

### 3. API & Client Generation

If you change a FastAPI router:

1.  Verify the backend types: `task backend:check`.
2.  Update the frontend SDK without a running API: `task api:generate`.

### 4. Releases

Pushes to `main` run the complete CI suite before the `release` workflow creates GitHub releases with the existing Renovate App. The separate `publish` workflow publishes the shared `camply` image to GHCR from the released full-version tag, or from the successful main SHA when no release is needed. `latest` tracks successful `main` builds; Gitmoji-driven releases also publish full-version tags, moving Docker/Git major aliases such as `v1`, and the `camply` wheel and sdist as GitHub release assets. Use `task dist` to build the artifacts locally. See [release operations](../operations/RELEASES.md) for version rules, repository permissions, local verification, and failure recovery.

---

## 🧪 Testing Discipline

### Backend

- Enforce module and optional dependency boundaries: `task backend:imports` (also included in `task backend:lint`, CI, and pre-commit).
- Run backend unit/integration tests: `task backend:test`
- Verify isolated wheel and sdist installations: `task backend:packaging:test`
- Verify artifact compatibility on the minimum Python: `task backend:packaging:test PACKAGING_PYTHON=3.11`
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

- Run visual snapshots & compare against baselines: `task snapshot` (set `CAMPLY_SNAPSHOT_PORT=5197` to isolate a worktree from another dev server)
- Update visual snapshot baselines: `task snapshot:update`
- Verify snapshots match baselines (CI regression check): `task snapshot:check`
- Rebuild the comparison gallery from saved screenshots: `task snapshot:report` (no Vite server or browser capture)
- View visual report: `tmp/snapshots/REPORT.md` (Markdown index) or open `tmp/snapshots/report.html` directly in your browser
- Verify snapshot navigation and the offline HTML viewer, and record desktop/mobile evidence: `task snapshot:verify` (requires Chromium via `task frontend:browser:install`)
- Run component DOM snapshots: `task frontend:test` (or `task test`)

The HTML gallery offers **Side by side**, **Reveal slider**, and **Highlighted diff** views. Search names, descriptions, viewports or themes and filter Modified, Unchanged or New screenshots. The reveal slider works with the keyboard. New screenshots explicitly show that no baseline existed and disable comparison modes that need one. Different screenshot sizes are padded to a common canvas, preserving alignment without stretching either image.

The HTML uses relative links to PNG files in `before/`, `current/`, and `diffs/` beside the report. Images remain separate files. Open the report directly through `file://` without a server or network connection. Keep those folders with the HTML when moving or sharing a comparison. The permanent viewer source is `src/frontend/tooling/snapshot-gallery.html`; the generated `tmp/snapshots/report.html` remains a local artifact excluded from Git.

Run `task snapshot` before accepting UI changes. `task snapshot:update` compares against the old baseline **before** replacing it, so the `before/` folder retains the old PNGs and the HTML links to the actual before/after images and metrics. Each command replaces the latest report and comparison files; copy the HTML together with `before/`, `current/`, and `diffs/` if you want to retain a review across future runs. `task snapshot:report` compares existing `current/` captures with the currently accepted `baselines/`, reports how many saved views were found, and never accepts new baselines. It requires at least one saved capture. The Markdown index uses saved `before/`, `current/`, and `diffs/` images beside it.

Visual regression checking is automated in GitHub Actions CI via the `ui-snapshots` workflow job, which installs headless Chromium, verifies the gallery with `task snapshot:verify`, executes `task snapshot:check` with deterministic test clocks, and uploads the report, local image folders and browser verification evidence on completion. Viewer evidence and a synthetic demo report with its image folders are available locally under `tmp/snapshot-gallery/` after verification. The comparison generator and browser verification script are included in frontend type checking.

Map snapshots navigate at `domcontentloaded` and wait for loaded search results, the rendered map and fixture markers. They do not depend on global network idleness, which background map requests can prevent. `task snapshot:verify` exercises navigation with a deliberately pending request and delayed result/map rendering before verifying the offline gallery.

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

### PostgreSQL search verification

Apply the search index migration with `task backend:migration-upgrade`. PostgreSQL's native full-text search and `pg_trgm` power autocomplete and Explore; no extra search service or credentials are required. SQLite development uses portable substring matching, so validate typo tolerance on PostgreSQL.

Run `task search:smoke` with Docker running. It starts a test-owned PostgreSQL 17 container on a random loopback port, applies the complete migration chain, verifies downgrade/re-upgrade, and tests synthetic search ranking, typos, cross-field tokens, filters, facets, pagination, and GIN index usage. It removes its container on completion. CI runs this as **PostgreSQL Search**; normal unit tests skip the opt-in suite.

### Map Discovery Verification

`task maps:verify` runs real map-query checks against a disposable PostgreSQL container, then serves a temporary synthetic SQLite application to Chromium. Install the browser first with `task frontend:browser:install`. Docker is required; live checks fail explicitly when unavailable and ordinary `task test` skips their opt-in entrypoints. No operator database or secret file is used.

The 5,000-place fixture proves all-pages discovery, bounded groups/member pagination, provider identity, view/history behavior, and map-failure recovery. It records timings, query plans, and browser screenshots under `tmp/maps-*`. Tile requests are intercepted locally so automation does not load public OSM tiles. `task snapshot` additionally covers maps at 375px/1440px in both themes and selected/error states. Inspect intended visual changes before `task snapshot:update`, then run `task snapshot:check`.

Frontend previews use their configured backend; publishing a frontend preview does not deploy the Python API. Map/list filtering requires both sides from the mapping interaction feature. Check `/api/openapi.json` for Explore's `west`, `south`, `east`, and `north` inputs, then compare `/api/search/explore` with and without a small viewport. An older API silently ignores unknown parameters and returns the full catalog, even when the frontend says “in map area.” Rebuild and restart the backend as well as the frontend before testing this feature.

Mapping setup needs no key by default. Public build-time overrides and production tile-source options are in [CONFIGURATION.md](../operations/CONFIGURATION.md). Changing source settings requires a frontend rebuild, including for Docker/static hosting.

## Root packaging and source archives

Root `pyproject.toml`/`uv.lock` and `package.json`/`pnpm-lock.yaml` own the environments. `tasks/python.yaml` and `tasks/frontend.yaml` both execute from the root. The `backend:*` namespace is retained for compatibility; it does not imply a nested Python project.

Run `uv run python -m build` after `task install`, or `python -m build` with the project interpreter. Standard checkout builds require Node 24 and pinned pnpm, install the frozen frontend dependency graph, and compile root-hosted `/api` assets. A missing toolchain or broken build is an error. The sdist contains rebuildable frontend inputs and prepared assets; its wheel can be rebuilt outside the repository without Node. Editable Python installs, dependency discovery, and Python-only checks do not compile the UI.

Generated assets and their private integrity manifest live under ignored `build/`. Wheels receive `camply/server/static`; sdists receive `src/camply/server/static` and the inventory. These are archive mappings, not generated files in working Python source. Modifying archived frontend inputs or corrupting its assets invalidates reuse and requires a fresh source build with the documented toolchain. See the [packaging contract](../specs/013-root-project-layout/contracts/packaging.md).

## Spec-Kit feature locations

Create and resume features under `docs/specs/NNN-feature-name`. `.specify/` remains at root; `SPECIFY_FEATURE_DIRECTORY` selects a complete feature directory, and ignored `.specify/feature.json` saves the current checkout's relative pointer. Old saved `specs/<feature>` pointers resolve to their relocated directory when it exists; read-only/no-persist operations do not rewrite state. Existing duplicate number prefixes retain distinct feature directories, and new numbering advances past the highest prefix.

The local Gemini specify command and shared shell creator both default to `docs/specs`. These managed defaults differ from upstream scaffolding: after refreshing Spec-Kit, run the feature workflow regressions in `tests/test_specify_workflows.py` and confirm no root `specs` directory is recreated. `AGENTS.md` is canonical; Claude and Gemini instruction files point to it.
