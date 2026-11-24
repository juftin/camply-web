# Tasks: Documentation Rework

**Input**: Design documents from `/docs/specs/030-docs-rework/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/editorial-standard.md`, `contracts/site-navigation.md`, `quickstart.md`

**Organization**: Tasks are grouped by phase and user story so each perspective can be implemented and verified incrementally.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`–`[US5]`) for story phases only
- Every task includes exact repository file paths

## Phase 1: Setup

**Purpose**: Ensure documentation build tooling is installed and capture ground-truth CLI, config, and Task defaults before editing pages.

- [x] T001 Install documentation and frontend dependencies via `task docs:install`, verify baseline `task docs:check` passes on `docs/`, and record baseline word/line counts (`wc -lw`) for active pages (`README.md`, `docs/*.md`, `docs/self-hosting/*.md`, `docs/development/*.md`, `docs/architecture/*.md`, `docs/operations/*.md`)
- [x] T002 [P] Audit current environment variables, defaults, and runtime constraints in `src/camply/server/config.py` and `src/camply/db/config.py`
- [x] T003 [P] Audit current CLI commands, options, and provider behavior in `src/camply/cli/` and `Taskfile.yaml` / `tasks/`

---

## Phase 2: Foundational (Verification & Editorial Guardrails)

**Purpose**: Establish shared automated checks in `tests/docs/test_docs.py` before rewriting content so every phase can validate links, navigation scoping, search rules, and editorial quality incrementally.

**CRITICAL**: Complete before story phases begin.

- [x] T004 Add reusable helper checks to `tests/docs/test_docs.py` verifying preserved route targets (`/docs/`, `/docs/using-camply`, `/docs/404.html`, `/docs/assets/camply.svg`), plus parameterized helpers for retired-page links (`configuration.md`, `development.md`) and internal GitHub blob links scoped to completed tracks
- [x] T005 [P] Add editorial-standard helper assertions to `tests/docs/test_docs.py` checking active rewritten pages (passed as an explicit track list that expands per completed story) for zero emoji-prefixed headings and zero banned filler openers per `docs/specs/030-docs-rework/contracts/editorial-standard.md`

**Checkpoint**: Verification helpers ready in `tests/docs/test_docs.py`.

---

## Phase 3: User Story 1 - Default Documentation View for Users and Self-Hosters (Priority: P1) 🎯 MVP

**Goal**: Make the documentation site and repository README default cleanly to **User Documentation** and **Self-Hosting**, placing technical and reference tracks behind a secondary navigation menu with scoped sidebars.

**Independent Test**: Build and preview the docs site (`task docs:serve`), open `/` and `/using-camply`, and confirm only User Documentation and Self-Hosting groups appear in the default sidebar and primary navbar while Technical & Architectural Documentation and Technical Reference sit behind the `Technical` dropdown.

- [x] T006 [US1] Configure the 4-item navbar (`User Guide`, `CLI`, `Self-Hosting`, `Technical` dropdown), path-scoped `themeConfig.sidebar` map, and initial search exclusions (`specs/**`, `PLAN.md`, `CHECKLIST.md`, `development/DESIGN_AGENTIC.md`, `development/AGENT_TROUBLESHOOTING.md`) in `docs/.vitepress/config.ts` per `docs/specs/030-docs-rework/contracts/site-navigation.md`
- [x] T007 [P] [US1] Rewrite the landing page in `docs/index.md` keeping the `# Find your next campsite` H1, highlighting User Documentation and Self-Hosting as primary actions, and placing subtle secondary pointers to `/technical/` and `/reference`
- [x] T008 [P] [US1] Create initial `docs/technical/index.md` hub stub so `/technical/` resolves cleanly at the MVP checkpoint, and rewrite `README.md` to mirror the User Documentation and Self-Hosting default focus with concise links to `https://camply.rocks`, `docs/index.md`, `docs/using-camply.md`, `docs/self-hosting/index.md`, and secondary links to `docs/technical/index.md` and `docs/reference.md`
- [x] T009 [US1] Add navigation-scoping assertions to `tests/docs/test_docs.py` verifying the default sidebar in `docs/.vitepress/config.ts` contains only User Documentation and Self-Hosting entries and does not expose `CHECKLIST`, `PLAN`, `DESIGN_AGENTIC`, `AGENT_TROUBLESHOOTING`, or `specs/`

**Checkpoint**: Default landing page, README, and VitePress navigation cleanly prioritize User Documentation and Self-Hosting.

---

## Phase 4: User Story 2 - Clear User Documentation for Web App and CLI (Priority: P1)

**Goal**: Deliver concise, plainspoken, non-duplicated **User Documentation** for both the web app and the `camply` CLI.

**Independent Test**: Follow `docs/using-camply.md` and `docs/cli.md` end-to-end to verify web scan creation, weekday/weekend filtering, Pushover user-key setup, CLI discovery, and CLI availability watching work with zero references to backend internals or spec TODOs.

- [x] T010 [P] [US2] Rewrite `docs/using-camply.md` (preserving `/docs/using-camply`) to cover finding campgrounds, creating/editing scans, weekday/night and minimum-stay rules, Pushover alerts, and first-time admin catalog sync without self-hosting or backend jargon
- [x] T011 [P] [US2] Rewrite `docs/cli.md` using verified CLI flags from `src/camply/cli/` to cover installation via `uv`, location discovery, availability watching, night/weekend/stay-length examples, and current CLI limitations in concise, plainspoken prose without spec-deferral jargon

**Checkpoint**: User Documentation (`docs/using-camply.md` and `docs/cli.md`) is self-contained, accurate, and ready for readers.

---

## Phase 5: User Story 3 - Focused Self-Hosting Documentation for Maintainers (Priority: P1)

**Goal**: Consolidate overlapping hosting and configuration instructions into one clear **Self-Hosting** track covering deployment choice, standalone, containers/Helm, everyday configuration, and maintenance.

**Independent Test**: Follow `docs/self-hosting/index.md` through `standalone.md`, `containers.md`, `configuration.md`, and `maintenance.md` to confirm every deployment model, auth mode, Pushover app setup, backup/restore step, and security warning is complete without consulting contributor or developer guides.

- [x] T012 [P] [US3] Create `docs/self-hosting/index.md` with a deployment comparison table (Standalone vs. Docker Compose vs. Kubernetes/Helm) and post-install checklist (initial catalog sync, auth, Pushover)
- [x] T013 [P] [US3] Rewrite `docs/self-hosting/standalone.md` for single-machine Python/SQLite hosting (`uvx`, `uv tool install`, prepared wheel, `--host`/`--port`, reverse-proxy `CAMPLY_APP_URL`) using relative site links
- [x] T014 [P] [US3] Rewrite `docs/self-hosting/containers.md` for Docker Compose quickstart/operations and Kubernetes/Helm overview linking to `deploy/helm/README.md` and relative Self-Hosting config pages
- [x] T015 [US3] Create `docs/self-hosting/configuration.md` consolidating `docs/configuration.md` around `CAMPLY_AUTH_MODE` (`none`, `session`, `auth0`), Pushover (`PUSHOVER_APP_TOKEN`, `CAMPLY_NOTIFICATION_MODE`, `CAMPLY_APP_URL`), storage (`CAMPLY_DB_HOST`), and polling intervals, verified against `src/camply/server/config.py` and `src/camply/db/config.py`
- [x] T016 [P] [US3] Create `docs/self-hosting/maintenance.md` covering SQLite/PostgreSQL backups and restores, schema upgrades, health checks, and common maintainer troubleshooting
- [x] T017 [US3] Remove retired `docs/configuration.md` after updating all inbound links across `docs/` and `README.md` to `docs/self-hosting/configuration.md`

**Checkpoint**: All five **Self-Hosting** pages are complete, deduplicated, and verified against `tests/docs/test_docs.py`.

---

## Phase 6: User Story 4 - Scoped Technical & Architectural Documentation and Technical Reference (Priority: P2)

**Goal**: Organize and rewrite **Technical and Architectural Documentation** for contributors, clean up **Technical Reference** without losing exact technical tables or historical specs, and configure search exclusion/deprioritization for internal artifacts.

**Independent Test**: Navigate via the `Technical` navbar dropdown to `/technical/` and `/reference`, verify scoped sidebars switch cleanly per perspective, verify zero overlap between `CONTRIBUTING.md` and `DEVELOPER_GUIDE.md`, and confirm search excludes `docs/specs/`, `PLAN.md`, `CHECKLIST.md`, and agent docs.

### Track A: Technical and Architectural Documentation

- [x] T018 [P] [US4] Finalize `docs/technical/index.md` summarizing repository layout (`src/camply/`, `src/frontend/`, `tasks/`, `deploy/`) and linking to rewritten contributor guides and architecture blueprints
- [x] T019 [P] [US4] Rewrite `docs/CONTRIBUTING.md` to focus strictly on PR workflow, `.worktrees/`, Gitmoji commits/PR titles, and review expectations without duplicating local environment setup
- [x] T020 [US4] Consolidate `docs/development.md` into `docs/development/DEVELOPER_GUIDE.md`, covering prerequisites, local stack (`task install`, `task compose:infra`, `task dev`), quality gates (`task lint`, `task check`, `task test`), and editing/previewing docs (`task docs:serve`, `task docs:check`)
- [x] T021 [US4] Remove retired `docs/development.md` after migrating docs-workflow notes to `docs/development/DEVELOPER_GUIDE.md` and updating all inbound links in `README.md`, `docs/index.md`, and `docs/`
- [x] T022 [P] [US4] Rewrite `docs/development/STYLE_GUIDE.md` to remove emoji headings/filler while keeping Python, React/TypeScript, testing/VCR, Gitmoji, and documentation editorial rules aligned with `docs/specs/030-docs-rework/contracts/editorial-standard.md`
- [x] T023 [P] [US4] Rewrite `docs/architecture/ARCHITECTURE_DEEP_DIVE.md` to present package layer boundaries and the smart de-duplicated polling engine clearly without copied boilerplate
- [x] T024 [P] [US4] Rewrite `docs/architecture/DESIGN_DATA.md` to document database models, availability snapshots, and notification outbox design concisely
- [x] T025 [P] [US4] Rewrite `docs/architecture/DESIGN_PROVIDERS.md` to explain provider abstractions, catalog sync/enrichment, and pacing/retries cleanly
- [x] T026 [P] [US4] Rewrite `docs/architecture/DESIGN_NOTIFICATIONS.md` to document summary vs. direct delivery, coalescing, and Pushover dispatch clearly
- [x] T027 [P] [US4] Rewrite `docs/architecture/DESIGN_API.md` to remove emoji headings and cover FastAPI routes, auth flows, health checks, and standalone serving concisely
- [x] T028 [P] [US4] Rewrite `docs/architecture/DESIGN_FRONTEND.md` to document React/Vite/MapLibre/TanStack Query architecture and docs-bundle integration concisely

### Track B: Technical Reference & Search Hygiene

- [x] T029 [P] [US4] Rewrite `docs/reference.md` as the **Technical Reference** hub linking cleanly to operations references, specifications catalog, roadmap/plan, checklist, and agent references
- [x] T030 [P] [US4] Clean up headings, relative links, and duplicated self-hosting intros in `docs/operations/CONFIGURATION.md` while preserving all `CAMPLY_*` environment-variable tables and defaults
- [x] T031 [P] [US4] Clean up headings, relative links, and duplicated standalone quickstarts in `docs/operations/RUNNING.md` while preserving package extras, role subcommands, build contracts, and enrichment CLI details
- [x] T032 [P] [US4] Clean up headings and relative links in `docs/operations/RELEASES.md` while preserving CI/semantic-release/PyPI/Docker/Helm/Pages pipeline accuracy
- [x] T033 [P] [US4] Clean up headings and relative links in `docs/development/DESIGN_AGENTIC.md`, `docs/development/AGENT_TROUBLESHOOTING.md`, `docs/PLAN.md`, and `docs/CHECKLIST.md` so all sit cleanly under Technical Reference with zero broken links
- [x] T034 [P] [US4] Verify `docs/specs/index.md` links cleanly to `docs/specs/030-docs-rework/` and existing spec directories without altering historical spec files under `docs/specs/`
- [x] T035 [US4] Tune local search document-boost options alongside the `_render` exclusions in `docs/.vitepress/config.ts` so User/Self-Hosting pages outrank `operations/` and `architecture/`
- [x] T036 [US4] Expand `tests/docs/test_docs.py` checks to enforce retired-link, internal-link, and editorial-standard assertions across all active tracks, plus search exclusion/boost configuration in `docs/.vitepress/config.ts`

**Checkpoint**: Both secondary tracks (**Technical and Architectural Documentation** and **Technical Reference**) have scoped sidebars, clean links, and search-filtered internal artifacts.

---

## Phase 7: User Story 5 - Human-Readable, Low-Noise Writing Style (Priority: P1)

**Goal**: Audit every rewritten page across User Documentation, Self-Hosting, and active Technical and Architectural Documentation against the "more is less" and anti-AI-slop rules and confirm search behavior prioritizes human guides.

**Independent Test**: Run automated editorial assertions in `tests/docs/test_docs.py`, review paragraph lengths and prose reductions across consolidated pages, and test local search queries in `task docs:serve`.

- [x] T037 [US5] Audit all active Markdown files in `docs/index.md`, `docs/using-camply.md`, `docs/cli.md`, `docs/self-hosting/*.md`, `docs/technical/index.md`, `docs/CONTRIBUTING.md`, `docs/development/{DEVELOPER_GUIDE,STYLE_GUIDE}.md`, and `docs/architecture/*.md` against `docs/specs/030-docs-rework/contracts/editorial-standard.md` (zero emoji headings, zero filler openers, paragraphs <=5 lines, >=30% redundant prose reduction on consolidated guides)
- [x] T038 [US5] Verify VitePress local search index output in `build/docs/` (via `tests/docs/test_docs.py` or search-index inspection) confirms excluded internal artifacts (`specs/`, `PLAN.md`, `CHECKLIST.md`, `DESIGN_AGENTIC.md`, `AGENT_TROUBLESHOOTING.md`) are absent from the built search index and queries like `"weekends"`, `"notifications"`, `"standalone"`, and `"login"` surface User/Self-Hosting pages first

**Checkpoint**: Editorial standard and search hygiene verified automatically and by human review.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify cross-repo references, run full docs/frontend/packaging/lint/type checks, and complete `quickstart.md` validation.

- [x] T039 [P] Verify `AGENTS.md` and `deploy/helm/README.md` relative/repo links resolve accurately against the updated `docs/` file layout
- [x] T040 Run `task docs:check`, `task lint`, and `task check` from repository root and resolve any failures
- [x] T041 Run `task frontend:build`, `task frontend:test`, and `uv run pytest tests/test_frontend_build.py tests/packaging/test_frontend_artifacts.py` to confirm bundled `/docs/` routes (`/docs/`, `/docs/using-camply`, `/docs/assets/camply.svg`, `/docs/404.html`) pass end-to-end
- [x] T042 Execute manual walkthrough in `docs/specs/030-docs-rework/quickstart.md` via `task docs:serve` and mark feature completion in `docs/CHECKLIST.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — establishes automated test guardrails in `tests/docs/test_docs.py`.
- **Phase 3 (US1 - Default View & Nav)**: Depends on Phase 2 — sets up `docs/.vitepress/config.ts`, `docs/index.md`, and `README.md`.
- **Phase 4 (US2 - User Docs)**: Depends on Phase 1 & Phase 2 (can run in parallel with US1 once `docs/.vitepress/config.ts` routes are settled).
- **Phase 5 (US3 - Self-Hosting)**: Depends on Phase 1 & Phase 2 (can run in parallel with US2).
- **Phase 6 (US4 - Technical & Architectural + Technical Reference)**: Depends on Phase 2 and US3 (needs `docs/self-hosting/configuration.md` before `operations/CONFIGURATION.md` and `README.md` cross-link cleanup; Track A and Track B tasks marked `[P]` run in parallel).
- **Phase 7 (US5 - Editorial Audit & Search Verification)**: Depends on Phases 3–6 so all rewritten pages and search config are audited together.
- **Phase 8 (Polish & Verification)**: Depends on Phase 7.

### User Story Dependencies

- **US1 (P1)**: MVP foundation for the documentation site's default two-perspective presentation.
- **US2 (P1)** and **US3 (P1)**: Independent of each other; both rely on US1 navigation routes and Phase 1 ground-truth audit.
- **US4 (P2)**: Independent from US2; coordinates link updates after US3 retires `docs/configuration.md`.
- **US5 (P1)**: Cross-cutting editorial and search-hygiene verification across US1–US4 outputs.

### Parallel Opportunities

- **Setup**: `T002` and `T003` run in parallel after `T001` (or alongside it).
- **US1**: `T007` (`docs/index.md`) and `T008` (`README.md`) run in parallel.
- **US2**: `T010` (`docs/using-camply.md`) and `T011` (`docs/cli.md`) run in parallel.
- **US3**: `T012`, `T013`, `T014`, `T016` run in parallel; `T015` runs alongside them before `T017` deletes `docs/configuration.md`.
- **US4**: `T018`, `T019`, `T022`–`T028`, and `T029`–`T034` touch separate files and can run in parallel batches.

---

## Parallel Example: User Story 3 (Self-Hosting)

```bash
# Rewrite independent Self-Hosting guides in parallel:
Task: "Create docs/self-hosting/index.md"
Task: "Rewrite docs/self-hosting/standalone.md"
Task: "Rewrite docs/self-hosting/containers.md"
Task: "Create docs/self-hosting/configuration.md"
Task: "Create docs/self-hosting/maintenance.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 + User Story 3)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational guardrails).
2. Complete Phase 3 (US1 — Default View, Navbar, Scoped Sidebars, README).
3. Complete Phase 4 (US2 — User Documentation) and Phase 5 (US3 — Self-Hosting).
4. **STOP and VALIDATE**: Run `task docs:check` and preview via `task docs:serve` to confirm the default two-perspective user/self-hoster experience works cleanly end-to-end.

### Full Delivery

5. Complete Phase 6 (US4 — Technical & Architectural Documentation, Technical Reference cleanup, and search filtering).
6. Complete Phase 7 (US5 — Editorial & Search Audit across all active pages).
7. Complete Phase 8 (Cross-repo links, frontend/packaging verification, and `docs/CHECKLIST.md` update).

---

## Phase 9: Convergence

- [x] T043 Update stale environment variable and path references (`REDIS_URL` → `CAMPLY_VALKEY_URL`, `DATABASE_URL` → `CAMPLY_DB_*`, `task frontend:codegen` → `task api:generate`, `frontend` → `src/frontend`, `backend-api`/`redis`/`postgres` → `backend`/`valkey`/`db`, `scripts/run-snapshots.ts` → `src/frontend/tooling/run-snapshots.ts`) in `docs/development/AGENT_TROUBLESHOOTING.md` and `docs/development/DESIGN_AGENTIC.md` per FR-008
- [x] T044 Switch VitePress sidebar to the unified collapsible 4-section layout, add client-side Mermaid rendering (`MermaidDiagram.vue`, `mermaid`, CSS overflow & race fixes), move licensing to `docs/license.md`, configure `boostDocument` search ranking, and align editorial/technical accuracy fixes per follow-up review
