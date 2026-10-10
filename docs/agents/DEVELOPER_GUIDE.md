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

---

## ✅ Pre-Commit & Linting

The project uses `pre-commit` to ensure code quality.

- Run manually: `task pre-commit`
- Auto-fix issues: `task fix`
