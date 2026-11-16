# Research: Documentation Rework

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

## Current Documentation Audit

An audit of `docs/` (~3,850 lines across 26 active pages plus 30+ feature spec directories under `docs/specs/`) and `README.md` identified four root causes of noise and redundancy:

1. **Unscoped navigation**: `docs/.vitepress/config.ts` exposes 7 top-level navbar groups (`Overview`, `Using camply`, `Self-hosting`, `Operations`, `Architecture`, `Development`, `Reference`) and expands all 6 sidebar sections globally. Everyday users and self-hosters see `CHECKLIST`, `PLAN`, `Agentic Tooling`, `Troubleshooting` (agent-focused), `DESIGN_*`, and `Specifications Catalog` next to `Using camply`.
2. **Cross-page duplication**:
   - Standalone setup (`uvx --from "camply-web[server]" camply serve`, SQLite storage, backups, default admin warning) is repeated across `README.md`, `docs/self-hosting/standalone.md`, `docs/operations/RUNNING.md`, `docs/operations/CONFIGURATION.md`, and `docs/development/DEVELOPER_GUIDE.md`.
   - Authentication and Pushover configuration appear in `docs/using-camply.md`, `docs/configuration.md`, `docs/operations/CONFIGURATION.md`, and `docs/development/DEVELOPER_GUIDE.md`.
   - Contributor quickstarts (`task install`, `task compose:infra`, `task dev`) are duplicated across `docs/CONTRIBUTING.md`, `docs/development.md`, and `docs/development/DEVELOPER_GUIDE.md`.
3. **AI-slop & dense prose patterns**:
   - Generic openers (`"Welcome to the Technical Reference hub"`, `"Thank you for your interest in contributing..."`, `"This document defines..."`).
   - Decorative emoji prefixes on headings (`⚙️ Core Configuration`, `📋 Prerequisites`, `🚀 Quickstart`, `🌳 Branching`, `🏷️ Commit`, `🧪 Testing`, `🎯 Vision`, `🏗️ Core Architecture`).
   - Long, dense walls of text mixing user workflows with internal migration history, deferred-TODO inventories, and implementation trivia (`docs/cli.md` lines 28–115, `docs/development/DEVELOPER_GUIDE.md` lines 33–55, `docs/operations/RUNNING.md` lines 45–50).
   - Spec-generated "Python package boundaries" / "Standalone storage" boilerplate prepended onto `docs/architecture/*.md`.
4. **Inconsistent links and stale references**:
   - Pages inside VitePress (`docs/configuration.md`, `docs/self-hosting/standalone.md`, `docs/self-hosting/containers.md`, `docs/development.md`) link to other pages on the same VitePress site via `https://github.com/juftin/camply-web/blob/main/docs/...` instead of relative Markdown links.
   - `docs/development.md` still refers to `docs/site` (a pre-consolidation directory).

## Key Technical Decisions

### 1. Scoped Multi-Sidebar Navigation in VitePress

- **Decision**: Use VitePress's path-keyed `themeConfig.sidebar` map so `"/"` (default landing, User Documentation, and Self-Hosting) shows only **User Documentation** and **Self-Hosting** groups, while secondary routes (`/technical`, `/development/`, `/architecture/`, `/CONTRIBUTING`) switch to the **Technical and Architectural Documentation** sidebar, and `/reference`, `/operations/`, `/specs/`, `/PLAN`, `/CHECKLIST` switch to the **Technical Reference** sidebar.
- **Rationale**: Keeps the default reader view focused on two perspectives without hiding or deleting deeper docs. One click from a compact top-right `Technical` dropdown in the navbar opens either secondary perspective with its own focused sidebar.
- **Alternatives considered**:
  - _Collapsed groups in one global sidebar_: Rejected because all four perspectives still appear in every page's sidebar and clutter mobile/desktop navigation.
  - _Separate VitePress builds_: Rejected because it breaks unified `/docs/` bundling, shared styling, and cross-perspective linking.

### 2. Search Hygiene via VitePress Local Search Filtering & Boosting

- **Decision**: Configure VitePress `themeConfig.search.options` (`_render` hook and/or MiniSearch `boostDocument`) to exclude internal engineering artifacts (`docs/specs/`, `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/development/DESIGN_AGENTIC.md`, `docs/development/AGENT_TROUBLESHOOTING.md`) from the default search index while keeping them published as readable HTML pages under Technical Reference, and boost User Documentation and Self-Hosting pages above `operations/` reference tables.
- **Rationale**: Currently `docs/specs/` contains 150+ Markdown files that flood local search results for everyday terms like "campground", "alerts", "weekends", or "standalone". Excluding internal artifacts from search while preserving their built HTML pages satisfies both `FR-003` and `tests/docs/test_docs.py` link checks.
- **Alternatives considered**:
  - _Excluding `docs/specs/` from VitePress `srcExclude`_: Rejected because Q2 explicitly required keeping specs, roadmaps, checklists, and agent docs published as pages inside Technical Reference.

### 3. Preserved Entrypoints & Governance Paths

- **Decision**: Preserve `/docs/` (`docs/index.md`), `/docs/using-camply` (`docs/using-camply.md`), `/docs/assets/camply.svg`, and `/docs/404.html` required by `src/frontend/components/Layout.tsx`, `src/frontend/tooling/verify-pages.ts`, and `tests/packaging/test_frontend_artifacts.py`. Also preserve repo-governed paths referenced by `AGENTS.md` and Spec-Kit (`docs/specs/`, `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/CONTRIBUTING.md`, `docs/development/DEVELOPER_GUIDE.md`, `docs/development/STYLE_GUIDE.md`, `docs/development/DESIGN_AGENTIC.md`, `docs/development/AGENT_TROUBLESHOOTING.md`, `docs/architecture/*.md`, `docs/operations/*.md`).
- **Rationale**: Preserves CI, Wrangler, wheel/sdist packaging checks, and Spec-Kit/agent conventions while freeing non-entrypoint subpages (`docs/configuration.md`, `docs/development.md`) to consolidate cleanly into the four-perspective structure.
- **Alternatives considered**:
  - _Moving every Markdown file into `docs/user/`, `docs/self-hosting/`, `docs/technical/`, `docs/reference/`_: Rejected because moving `docs/specs/` or `docs/architecture/` would break `AGENTS.md`, `deploy/helm/README.md`, and cross-spec relative links without adding user value. Path-keyed sidebars in VitePress decouple URL layout from sidebar presentation cleanly.

### 4. Rewriting Depth & Accuracy Verification

- **Decision**: Rewrite `docs/index.md`, `README.md`, `docs/using-camply.md`, `docs/cli.md`, `docs/self-hosting/*`, `docs/CONTRIBUTING.md`, `docs/development/DEVELOPER_GUIDE.md`, `docs/development/STYLE_GUIDE.md`, `docs/technical.md` (or `docs/technical/index.md`), `docs/reference.md`, and active `docs/architecture/*.md` guides for plainspoken human readability ("more is less"). Clean up headings, links, and duplicate prose in `docs/operations/*.md` while preserving complete environment-variable and runtime tables. Leave `docs/specs/**` untouched.
- **Rationale**: Matches Q3 (`FR-005`) and prevents losing exact configuration defaults or rewriting historical specs. Every command, flag, and env var will be verified directly against `src/camply/server/config.py`, `src/camply/db/config.py`, `src/camply/cli/`, `Taskfile.yaml`, and `tasks/*.yaml`.
- **Alternatives considered**:
  - _Rewriting `CONFIGURATION.md` into short prose only_: Rejected because maintainers and engineers rely on a single complete variable table in Technical Reference.
