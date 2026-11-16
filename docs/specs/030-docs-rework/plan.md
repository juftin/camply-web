# Implementation Plan: Documentation Rework

**Branch**: `030-docs-rework` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/docs/specs/030-docs-rework/spec.md`

## Summary

Reorganize and rewrite the `camply` documentation around four perspectives—**User Documentation**, **Self-Hosting**, **Technical and Architectural Documentation**, and **Technical Reference**—while defaulting the site landing page, navbar, and sidebar to **User Documentation** and **Self-Hosting**. Place the two smaller-audience technical perspectives behind a secondary `Technical` navbar dropdown with path-scoped VitePress sidebars, exclude internal engineering artifacts (`docs/specs/`, `PLAN.md`, `CHECKLIST.md`, agent guides) from local search while keeping them published under Technical Reference, consolidate duplicate guides, and rewrite active prose to a crisp "more is less" human editorial standard.

## Technical Context

**Language/Version**: Markdown, TypeScript/Vue 3 (VitePress `^1.6.4`), Node.js >=24 (`pnpm@12.15.0`), Python 3.14 (verification tests)

**Primary Dependencies**: `vitepress` (devDependency in `package.json`), `pyyaml` (Python test suite)

**Storage**: Static Markdown and VitePress configuration under `docs/` plus root `README.md`; static build output in `build/docs/`

**Testing**: `task docs:check` (`vitepress build docs` + `tests/docs/test_docs.py`), `task lint`, `task check`, `tests/test_frontend_build.py`, `tests/packaging/test_frontend_artifacts.py`, `src/frontend/tooling/verify-pages.ts`

**Target Platform**: Bundled static `/docs/` site (Python standalone, Nginx, Cloudflare Pages), GitHub Pages mirror (`juftin.com/camply-web/`), and GitHub repository Markdown views

**Project Type**: Documentation site and repository documentation

**Performance Goals**: Zero VitePress build warnings/errors; local search surfaces User Documentation and Self-Hosting pages at the top for everyday queries without spec/checklist noise

**Constraints**: Preserve `/docs/`, `/docs/using-camply`, `/docs/assets/camply.svg`, `/docs/404.html`, and repo-governed paths (`docs/specs/`, `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/development/*`, `docs/architecture/*`, `docs/operations/*`); keep VitePress isolated from Python runtime dependencies

**Scale/Scope**: ~25 active documentation pages + `README.md` + `docs/.vitepress/config.ts` + automated verification in `tests/docs/test_docs.py` (150+ historical spec files under `docs/specs/` remain untouched)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- **I. Reliability & Precision**: Every documented CLI flag, environment variable, default value, auth mode, notification option, and Task target will be verified against current code (`src/camply/server/config.py`, `src/camply/db/config.py`, `src/camply/cli/`, `Taskfile.yaml`, `tasks/*.yaml`). **PASS**.
- **II. Type Safety & Static Analysis**: Changes to `docs/.vitepress/config.ts` and `tests/docs/test_docs.py` must pass `task lint` (`ruff`, `oxlint`, `oxfmt`) and `task check` (`mypy`, `tsc`). **PASS**.
- **III. Modern Workflow & Automation**: Documentation preview, build, and checks remain driven through `task docs:serve`, `task docs:build`, `task docs:preview`, and `task docs:check`. **PASS**.
- **IV. Monorepos & Separation of Concerns**: VitePress remains a frontend/docs JS devDependency only; generated docs remain bundled into `src/frontend/dist/docs/` and Python distributions without changing runtime boundaries. **PASS**.
- **V. Automated Verification**: Extend `tests/docs/test_docs.py` with automated assertions for scoped sidebars, search exclusions for internal artifacts, and editorial hygiene (no emoji-prefixed headings or banned boilerplate openers in active tracks), alongside existing rendered-link/asset checks. **PASS**.

_Post-Phase 1 re-check_: Design artifacts (`data-model.md`, `contracts/*`, `quickstart.md`) preserve all packaging boundaries, entry routes (`/docs/`, `/docs/using-camply`), and repository governance paths with zero constitution violations.

## Project Structure

### Documentation (this feature)

```text
docs/specs/030-docs-rework/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── contracts/
    ├── editorial-standard.md
    └── site-navigation.md
```

### Repository Paths Affected

```text
README.md                               # Concise front door aligned to User + Self-Hosting default
AGENTS.md                               # Update any consolidated doc pointer if needed
docs/
├── .vitepress/config.ts                # 4-item navbar, path-scoped sidebars, search filtering/boosting
├── index.md                            # Default landing page (User + Self-Hosting primary; secondary Tech/Ref links)
├── using-camply.md                     # Rewritten Web App user guide (preserved URL)
├── cli.md                              # Rewritten CLI user guide (concise, non-spec prose)
├── self-hosting/
│   ├── index.md                        # New deployment comparison & post-install checklist
│   ├── standalone.md                   # Rewritten single-machine Python/SQLite guide
│   ├── containers.md                   # Rewritten Docker Compose & Helm overview
│   ├── configuration.md                # Consolidated maintainer config (replaces docs/configuration.md)
│   └── maintenance.md                  # New backups, restores, upgrades, and troubleshooting guide
├── technical/
│   └── index.md                        # Entry hub for Technical and Architectural Documentation
├── CONTRIBUTING.md                     # Rewritten PR, worktree, and Gitmoji commit workflow
├── development/
│   ├── DEVELOPER_GUIDE.md              # Consolidated dev setup, tasks, testing, and docs editing (absorbs docs/development.md)
│   ├── STYLE_GUIDE.md                  # Rewritten coding, testing, and documentation editorial rules
│   ├── DESIGN_AGENTIC.md               # Structural/heading cleanup (Technical Reference, search-excluded)
│   └── AGENT_TROUBLESHOOTING.md        # Structural/heading cleanup (Technical Reference, search-excluded)
├── architecture/
│   ├── ARCHITECTURE_DEEP_DIVE.md       # Rewritten polling engine & package layers
│   ├── DESIGN_DATA.md                  # Rewritten multi-tenant schema & outbox model
│   ├── DESIGN_PROVIDERS.md             # Rewritten provider contract, ingestion & enrichment
│   ├── DESIGN_NOTIFICATIONS.md         # Rewritten notification outbox & Pushover delivery
│   ├── DESIGN_API.md                   # Rewritten API contract, auth, and standalone serving
│   └── DESIGN_FRONTEND.md              # Rewritten frontend architecture & build pipeline
├── reference.md                        # Technical Reference entry hub
├── operations/
│   ├── CONFIGURATION.md                # Heading/link cleanup; complete env-var tables preserved
│   ├── RUNNING.md                      # Deduplicated runtime/packaging/CLI-subcommand reference
│   └── RELEASES.md                     # Heading/link cleanup; CI/release pipeline preserved
├── PLAN.md                             # Search-excluded under Technical Reference
├── CHECKLIST.md                        # Search-excluded under Technical Reference
└── specs/                              # Unchanged historical specs; search-excluded under Technical Reference
tests/docs/test_docs.py                 # Extended checks for nav scoping, search hygiene, and editorial rules
```

**Structure Decision**: Keep existing repo-governed directories (`docs/architecture/`, `docs/development/`, `docs/operations/`, `docs/specs/`, `docs/PLAN.md`, `docs/CHECKLIST.md`) and preserved entrypoint files (`docs/index.md`, `docs/using-camply.md`) in place, retire only the two redundant root files (`docs/configuration.md` and `docs/development.md`), add `docs/self-hosting/index.md`, `docs/self-hosting/configuration.md`, `docs/self-hosting/maintenance.md`, and `docs/technical/index.md`, and use VitePress path-scoped sidebars + search filtering to separate the four perspectives cleanly.

## Implementation Phases

1. **Navigation, Search & Verification Guardrails**
   - Update `docs/.vitepress/config.ts` with the 4-entry top navbar (`User Guide`, `CLI`, `Self-Hosting`, `Technical` dropdown), path-keyed scoped sidebars (default User + Self-Hosting vs. Technical & Architectural vs. Technical Reference), and local search `_render` / MiniSearch options excluding `specs/`, `PLAN.md`, `CHECKLIST.md`, `DESIGN_AGENTIC.md`, and `AGENT_TROUBLESHOOTING.md` while boosting User and Self-Hosting pages.
   - Extend `tests/docs/test_docs.py` to assert navigation scoping, search exclusion config, absence of retired-file links, and editorial-rule compliance (no emoji-prefixed headings or banned boilerplate openers in active tracks).
2. **Perspective 1 & 2 Rewrite (Default View: User Documentation + Self-Hosting + README)**
   - Rewrite `README.md`, `docs/index.md`, `docs/using-camply.md`, and `docs/cli.md` against current CLI/web behavior and the editorial standard.
   - Author/rewrite `docs/self-hosting/index.md`, `docs/self-hosting/standalone.md`, `docs/self-hosting/containers.md`, `docs/self-hosting/configuration.md`, and `docs/self-hosting/maintenance.md`; remove `docs/configuration.md`.
3. **Perspective 3 Rewrite (Technical and Architectural Documentation)**
   - Author `docs/technical/index.md`, rewrite `docs/CONTRIBUTING.md`, `docs/development/DEVELOPER_GUIDE.md` (absorbing `docs/development.md`), and `docs/development/STYLE_GUIDE.md`; remove `docs/development.md`.
   - Rewrite `docs/architecture/*.md` to remove boilerplate prefixes, emoji headings, and cross-page repetition while preserving accurate architectural explanations.
4. **Perspective 4 Cleanup (Technical Reference) & Cross-Repo Links**
   - Clean up headings, relative links, and self-hosting overlap in `docs/reference.md` and `docs/operations/{CONFIGURATION,RUNNING,RELEASES}.md` without stripping reference tables.
   - Clean up headings/links in `docs/development/{DESIGN_AGENTIC,AGENT_TROUBLESHOOTING}.md`; verify `AGENTS.md` and `deploy/helm/README.md` links resolve cleanly.
5. **Validation**
   - Run `task docs:check`, `task lint`, `task check`, `task frontend:build`, `tests/test_frontend_build.py`, and `tests/packaging/test_frontend_artifacts.py`, plus a visual walkthrough via `task docs:serve`.

## Complexity Tracking

No constitution violations; complexity tracking not required.
