# AGENTS.md

## Project Overview

**`camply`**, the campsite finder ⛺️, is a tool to help you book a campsite online. It is transitioning from a legacy CLI tool into a modern, full-stack, community-facing web application.

## 📚 Key Documentation & Pointers

Before modifying the system, review the relevant architectural blueprints:

- 👉 **[Roadmap & Plan](docs/PLAN.md)**: The definitive path forward and current phases.
- 👉 **[Feature Checklist](docs/CHECKLIST.md)**: Granular implementation tasks. (Update this before every PR!).
- 👉 **[Developer Guide](docs/development/DEVELOPER_GUIDE.md)**: Quickstart, workflows, and local setup.
- 👉 **[Style Guide](docs/development/STYLE_GUIDE.md)**: Engineering, Git, and PR standards.
- 👉 **[Architecture Deep Dive](docs/architecture/ARCHITECTURE_DEEP_DIVE.md)**: Details on the Smart De-duplicated Poller.
- 👉 **[Database Schema](docs/architecture/DESIGN_DATA.md)**: Details on the multi-tenant architecture and de-duplicated polling strategy.
- 👉 **[Provider Architecture](docs/architecture/DESIGN_PROVIDERS.md)**: The standard interface for integrating campsite booking APIs.
- 👉 **[Notification Architecture](docs/architecture/DESIGN_NOTIFICATIONS.md)**: Standarized multi-channel alerts.
- 👉 **[API Contract & Security](docs/architecture/DESIGN_API.md)**: FastAPI endpoints and Auth0/Whitelist logic.
- 👉 **[Frontend Journey](docs/architecture/DESIGN_FRONTEND.md)**: UX flows and Shadcn/UI design system.
- 👉 **[Agentic Tooling](docs/development/DESIGN_AGENTIC.md)**: Configuration for MCP servers (Local Dev & Agent workflows).
- 👉 **[Configuration](docs/operations/CONFIGURATION.md)**: Environment variables and settings.
- 👉 **[Troubleshooting](docs/development/AGENT_TROUBLESHOOTING.md)**: Solutions for common local dev issues.
- 👉 **[Project Constitution](.specify/memory/constitution.md)**: Core engineering principles and governance rules.

## 🤖 Agent Lifecycle & Spec-Kit

This project uses **Spec-Kit** for formal feature definition and task tracking.

1. **Research**: Use `/speckit.analyze` to audit existing logic.
2. **Specify**: Use `/speckit.specify` to define user stories and requirements in a `spec.md`.
3. **Design**: Use `/speckit.plan` to create a `plan.md` for the technical implementation.
4. **Tasking**: Use `/speckit.tasks` to generate a `tasks.md` with granular implementation steps.
5. **Implementation**: Mark tasks as completed in your feature's `tasks.md`.
6. **Closing**: Update the global **[docs/CHECKLIST.md](docs/CHECKLIST.md)** before finalizing your PR.

## 🏗️ Directory Structure

- `src/camply/`: One `camply` Python distribution, managed from root `pyproject.toml` and `uv.lock`.
  - `server/`: FastAPI, standalone runtime, and installed Gunicorn configuration (`server` extra).
  - `db/`: Models, SQLite persistence, and packaged Alembic migrations.
  - `providers/`: Third-party booking providers.
  - `worker/`: Shared polling engine and Celery adapters (`distributed` extra).
- `src/frontend/`: React TypeScript application, colocated tests, public assets, Pages `functions/`, and Node `tooling/`; manifests/configuration live at root.
- `src/camply/cli/`: The `camply` command-line entrypoint (base dependencies only; currently `--version`/`--help`). The existing `populate-database` utility is retained.
- `docs/{development,architecture,operations}/`: Current guides and design blueprints.
- `docs/specs/`: Feature specifications, plans, and task tracking. Spec-Kit creation defaults and numbering use this directory; `.specify/` stays at root. Feature overrides identify the complete feature directory, and saved pointers remain checkout-local.
- `tests/`: Python suites, installed-artifact/release regressions, and frontend visual baselines.
- `taskfiles/`: Python/frontend task definitions included by root `Taskfile.yaml`; preserve task namespaces and root working directories.
- `deploy/`: Infrastructure configuration. Root Dockerfile has backend/frontend targets; root Compose contains all services.
- `build/`, `dist/`, `tmp/`: Ignored generated frontend/API output, distributions, and reports respectively. Build hooks map assets into archives without staging into working source.
- `.worktrees/`: Git worktrees directory for parallel isolated development.

## ⚙️ Technology Stack & Standards

- **Backend**: Python >=3.11 managed by `uv`; Python 3.14 defaults for development, CI, Docker, and releases. Explicit compatibility checks use 3.11. FastAPI for web services.
- **Frontend**: React 18+ with TypeScript, built via Vite. Tailwind CSS + Shadcn/UI.
- **Database**: PostgreSQL (SQLAlchemy + Alembic).
- **Worker**: Smart De-duplicated Poller (Celery + Valkey).
- **Infrastructure**: Docker & Docker Compose.
- **API**: OpenAPI with automated TypeScript client generation.
- **Quality Gates**: `mypy`, Import Linter, native TypeScript 7, `ruff`, `oxlint`, `oxfmt`, `pytest`, `vitest`.

## 🌳 Working with Git Worktrees

To keep feature development isolated and avoid messing up the main repository state, we use git worktrees in the `.worktrees/` directory:

1. Create a new worktree for your feature:
   ```bash
   git worktree add .worktrees/feature-name -b feature-name
   ```
2. Navigate into the worktree to perform changes:
   ```bash
   cd .worktrees/feature-name
   ```
3. Once completed, you can remove the worktree:
   ```bash
   git worktree remove .worktrees/feature-name
   ```

## 🛠️ Development Tasks

All commands use `go-task` (`Taskfile.yaml`) for consistent execution.

- **Setup & Install**:
  - `task install`: Install all dependencies (backend + frontend).
- **Local Development**:
  - `task dev`: Run full stack development (API, Frontend, Database).
  - `task backend:dev`: Run just the backend API in debug mode.
  - `task frontend:dev`: Run just the frontend Vite server.
- **Code Quality**:
  - `task fix`: Automatically fix issues with linters and formatters (`ruff`, `oxlint`, `oxfmt`).
  - `task lint`: Run linters across the codebase.
  - `task check`: Run static type checking (`mypy` for backend, `tsc` for frontend).
  - `task backend:imports`: Enforce internal layers and optional dependency boundaries (also included in lint and pre-commit).

## 🧪 Testing Locally

The project mandates automated verification for all features. Tests must be written and executed locally before proposing changes.

- **Run all tests**:
  - `task test`: Executes tests across the entire monorepo.
- **Run specific test suites**:
  - `task backend:test`: Run Python tests via `pytest`. (Uses `pytest-vcr` for mock API responses).
  - `task frontend:test`: Run React tests via `vitest` and Testing Library.
- **Test-First Workflow**:
  - Ensure you write or update tests alongside your feature logic. Run the specific test you are working on directly if needed (e.g. `uv run pytest path/to/test.py`).

### 🔄 VCR Cassette Maintenance

To ensure tests remain accurate as external provider APIs evolve, we follow a regular renewal plan:

- **Frequency**: Every 30 days or whenever a provider API changes its response structure.
- **How to Renew**: Run the test suite with the record mode enabled (requires valid API credentials):
  ```bash
  task backend:test -- --vcr-record=all
  ```
- **Validation**: After renewing, verify the new cassettes don't contain sensitive credentials before committing.

## ✅ Pull Request Checklist

Before creating a PR, agents and contributors must ensure the following:

- [ ] **Tests Pass**: `task test` completes successfully without errors.
- [ ] **Type Check Passes**: `task check` returns no type violations.
- [ ] **Linting Passes**: `task lint` is clean (run `task fix` to resolve auto-fixable issues).
- [ ] **Architecture Aligned**: Code changes respect the `DESIGN_*.md` blueprints and `.specify/memory/constitution.md`.
- [ ] **Database Migrations**: If database models were changed, a new Alembic migration was generated and applied (`task backend:migration -- "message"`).
- [ ] **Documentation Updated**: If core logic or APIs changed, current `docs/` guides and OpenAPI specifications are updated accordingly.
