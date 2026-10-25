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

- Run visual snapshots & compare against baselines: `task snapshot` (set `CAMPLY_SNAPSHOT_PORT=5197` to isolate a worktree from another dev server)
- Update visual snapshot baselines: `task snapshot:update`
- Verify snapshots match baselines (CI regression check): `task snapshot:check`
- Rebuild the comparison gallery from saved screenshots: `task snapshot:report` (no Vite server or browser capture)
- View visual report: `frontend/snapshots/REPORT.md` (Markdown index) or open `frontend/snapshots/report.html` directly in your browser
- Verify the offline HTML viewer and record desktop/mobile evidence: `task snapshot:verify` (requires Chromium via `task frontend:browser:install`)
- Run component DOM snapshots: `task frontend:test` (or `task test`)

The HTML gallery offers **Side by side**, **Reveal slider**, and **Highlighted diff** views. Search names, descriptions, viewports or themes and filter Modified, Unchanged or New screenshots. The reveal slider works with the keyboard. New screenshots explicitly show that no baseline existed and disable comparison modes that need one. Different screenshot sizes are padded to a common canvas, preserving alignment without stretching either image.

Every PNG, style and control is embedded in the exported HTML: copy or rename this single file to keep a review, open it offline through `file://`, or share it without a server or adjacent image folders. The permanent viewer source is `frontend/scripts/snapshot-gallery.html`; the generated `frontend/snapshots/report.html` is a local artifact excluded from Git because embedded screenshots can make it large.

Run `task snapshot` before accepting UI changes. `task snapshot:update` compares against the old baseline **before** replacing it, so its HTML report retains the actual before/after images and metrics. Each command replaces the latest report; copy the HTML elsewhere if you want to retain that comparison across future runs. `task snapshot:report` compares existing `current/` captures with the currently accepted `baselines/`, reports how many saved views were found, and never accepts new baselines. It requires at least one saved capture. The Markdown index uses saved `before/`, `current/`, and `diffs/` images beside it.

Visual regression checking is automated in GitHub Actions CI via the `ui-snapshots` workflow job, which installs headless Chromium, verifies the gallery with `task snapshot:verify`, executes `task snapshot:check` with deterministic test clocks, and uploads the standalone report, image comparisons and browser verification evidence on completion. Viewer evidence and a small synthetic demo report are available locally under `frontend/tmp/snapshot-gallery/` after verification. The comparison generator and browser verification script are included in frontend type checking.

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

The 5,000-place fixture proves all-pages discovery, bounded groups/member pagination, provider identity, view/history behavior, and map-failure recovery. It records timings, query plans, and browser screenshots under `frontend/tmp/maps-*`. Tile requests are intercepted locally so automation does not load public OSM tiles. `task snapshot` additionally covers maps at 375px/1440px in both themes and selected/error states. Inspect intended visual changes before `task snapshot:update`, then run `task snapshot:check`.

Frontend previews use their configured backend; publishing a frontend preview does not deploy the Python API. Map/list filtering requires both sides from the mapping interaction feature. Check `/api/openapi.json` for Explore's `west`, `south`, `east`, and `north` inputs, then compare `/api/search/explore` with and without a small viewport. An older API silently ignores unknown parameters and returns the full catalog, even when the frontend says “in map area.” Rebuild and restart the backend as well as the frontend before testing this feature.

Mapping setup needs no key by default. Public build-time overrides and production tile-source options are in [CONFIGURATION.md](CONFIGURATION.md). Changing source settings requires a frontend rebuild, including for Docker/static hosting.
