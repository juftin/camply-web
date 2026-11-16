# Information Architecture & Content Model: Documentation Rework

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

## Entities

### 1. Documentation Perspective

| Perspective                                   | Default Visibility                                  | Target Reader                                                     | Tone & Depth                                                                            |
| --------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **User Documentation**                        | Primary (default landing & sidebar)                 | Campers using `camply.rocks`, self-hosted web UI, or `camply` CLI | Task-oriented, plainspoken, concrete examples, zero backend internals                   |
| **Self-Hosting**                              | Primary (default landing & sidebar)                 | Maintainers running their own camply instance                     | Practical deployment paths, required config tables, security & backup steps             |
| **Technical and Architectural Documentation** | Secondary (dropdown/secondary link, scoped sidebar) | Contributors and engineers studying how camply works              | Clear system explanations, local dev workflow, quality gates, no duplicated quickstarts |
| **Technical Reference**                       | Secondary (dropdown/secondary link, scoped sidebar) | Engineers and advanced operators needing exact contracts          | Exhaustive tables, runtime/packaging specs, release pipeline, specs & planning index    |

### 2. Canonical Page Map

#### Repository Front Door

- `README.md`: Concise project summary, link to `camply.rocks`, 3-line standalone quickstart, pointers to User Documentation, Self-Hosting, and secondary Technical/Reference entry points.

#### Perspective 1: User Documentation (Default Sidebar)

- `docs/index.md` (`/docs/`): Landing page introducing camply with clear starting points for **User Documentation** and **Self-Hosting**, plus subtle secondary links to **Technical and Architectural Documentation** and **Technical Reference**. Retains `# Find your next campsite` H1 for `verify-pages.ts` compatibility.
- `docs/using-camply.md` (`/docs/using-camply`, preserved): Web app guide — exploring campgrounds, creating/editing scans, weekday/night & stay-length rules, Pushover alerts, and first-time admin catalog sync note.
- `docs/cli.md` (`/docs/cli`): Terminal guide — installing `camply-web` with `uv`, discovering providers/recreation areas/campgrounds, watching availability, weekday/weekend and stay-length matching, and current CLI scope (brief, honest, non-spec-jargon).

#### Perspective 2: Self-Hosting (Default Sidebar)

- `docs/self-hosting/index.md` (`/docs/self-hosting/`): Choosing a deployment model — side-by-side comparison of Standalone, Docker Compose, and Kubernetes/Helm, plus initial post-install steps (sync catalog, set auth, configure Pushover).
- `docs/self-hosting/standalone.md` (`/docs/self-hosting/standalone`): Single-process Python + SQLite setup (`uvx` / `uv tool` / prepared wheel), listener flags, reverse-proxy `CAMPLY_APP_URL`.
- `docs/self-hosting/containers.md` (`/docs/self-hosting/containers`): Docker Compose stack and Kubernetes/Helm overview (linking to `deploy/helm/README.md`).
- `docs/self-hosting/configuration.md` (`/docs/self-hosting/configuration`, consolidating `docs/configuration.md`): Everyday configuration for maintainers — authentication modes (`none`, `session`, `auth0`), Pushover notifications (`PUSHOVER_APP_TOKEN`, `CAMPLY_NOTIFICATION_MODE`, `CAMPLY_APP_URL`), storage, and polling intervals, with relative link to full reference.
- `docs/self-hosting/maintenance.md` (`/docs/self-hosting/maintenance`): Backups, restores, schema upgrades, health checks, and common operational troubleshooting.

#### Perspective 3: Technical and Architectural Documentation (Scoped Secondary Sidebar)

- `docs/technical/index.md` (`/docs/technical/`): Entry hub for contributors — how the codebase is laid out (`src/camply/`, `src/frontend/`, `tasks/`, `deploy/`) and reading order.
- `docs/CONTRIBUTING.md` (`/CONTRIBUTING`, repo-governed path preserved): Pull request workflow, worktrees, Gitmoji commit/PR conventions, and review checklist (no duplicated local install guide).
- `docs/development/DEVELOPER_GUIDE.md` (`/development/DEVELOPER_GUIDE`, repo-governed path preserved; absorbs `docs/development.md`): Local development setup (`task install`, `task compose:infra`, `task dev`), quality gates (`task lint`, `task check`, `task test`), and working on/previewing the docs site.
- `docs/development/STYLE_GUIDE.md` (`/development/STYLE_GUIDE`, repo-governed path preserved): Backend Python, frontend React/TS, testing (VCR), and documentation editorial standards.
- `docs/architecture/ARCHITECTURE_DEEP_DIVE.md`: Package layer boundaries and the smart de-duplicated polling engine.
- `docs/architecture/DESIGN_DATA.md`: Multi-tenant database schema, availability snapshots, and outbox model.
- `docs/architecture/DESIGN_PROVIDERS.md`: Provider abstraction, catalog ingestion/enrichment, and rate limiting.
- `docs/architecture/DESIGN_NOTIFICATIONS.md`: Notification outbox, coalescing, summary vs. direct delivery, and Pushover integration.
- `docs/architecture/DESIGN_API.md`: FastAPI contract, health/readiness endpoints, authentication flows, and standalone asset serving.
- `docs/architecture/DESIGN_FRONTEND.md`: React/Vite/MapLibre/TanStack Query user journeys and build integration.

#### Perspective 4: Technical Reference (Scoped Secondary Sidebar)

- `docs/reference.md` (`/reference`): Entry hub for exact configuration tables, runtime/packaging rules, release operations, specifications, and internal project records.
- `docs/operations/CONFIGURATION.md`: Complete `CAMPLY_*` environment variable reference (cleaned headings/links; exact defaults preserved).
- `docs/operations/RUNNING.md`: Package extras, role subcommands (`serve frontend|backend|worker|beat`), wheel/sdist build contract, and enrichment CLI/task details (cleaned without duplicating Self-Hosting quickstarts).
- `docs/operations/RELEASES.md`: CI/CD, semantic-release, container/PyPI/Helm/Pages publication pipeline.
- `docs/specs/index.md` + `docs/specs/**`: Specifications Catalog and historical feature specs (preserved intact; excluded from default search).
- `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/development/DESIGN_AGENTIC.md`, `docs/development/AGENT_TROUBLESHOOTING.md`: Internal engineering/agent governance documents (preserved in-repo and reachable under Technical Reference; excluded from default search).

### 3. Consolidated / Retired Pages

- `docs/configuration.md` → Consolidated into `docs/self-hosting/configuration.md` (with `docs/operations/CONFIGURATION.md` serving as exhaustive reference).
- `docs/development.md` → Consolidated into `docs/development/DEVELOPER_GUIDE.md`.
- Any references in `docs/` or `README.md` to retired paths are updated so `tests/docs/test_docs.py` reports zero broken links.
