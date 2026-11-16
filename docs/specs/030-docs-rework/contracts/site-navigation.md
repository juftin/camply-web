# Contract: Site Navigation, Scoped Sidebars & Search Hygiene

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

## 1. Top Navigation Bar (`docs/.vitepress/config.ts`)

Top-level navigation MUST present only four concise entries, keeping the primary bar focused on Users and Self-Hosters:

1. `User Guide` → `/using-camply`
2. `CLI` → `/cli`
3. `Self-Hosting` → `/self-hosting/`
4. `Technical` _(dropdown)_:
   - `Architecture & Contributing` → `/technical/`
   - `Technical Reference` → `/reference`

## 2. Scoped Sidebars (`themeConfig.sidebar`)

| Route Prefix                                                                                                                        | Active Sidebar Groups                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/` (default: `/`, `/using-camply`, `/cli`, `/self-hosting/*`)                                                                      | **User Documentation** (`Overview`, `Web App`, `Command Line`) and **Self-Hosting** (`Overview`, `Standalone`, `Docker & Kubernetes`, `Configuration`, `Maintenance`)                                                                 |
| `/technical/`, `/CONTRIBUTING`, `/development/DEVELOPER_GUIDE`, `/development/STYLE_GUIDE`, `/architecture/`                        | **Technical & Architectural Documentation** (`Overview`, `Contributing`, `Development Setup`, `Style & Testing`, plus Architecture group: `Polling Engine`, `Data Model`, `Providers`, `Notifications`, `API & Security`, `Frontend`) |
| `/reference`, `/operations/`, `/specs/`, `/PLAN`, `/CHECKLIST`, `/development/DESIGN_AGENTIC`, `/development/AGENT_TROUBLESHOOTING` | **Technical Reference** (`Reference Hub`, `Environment Variables`, `Runtime & Packaging`, `Release Operations`, `Specifications Catalog`, `Roadmap & Plan`, `Feature Checklist`, `Agentic Tooling`, `Agent Troubleshooting`)          |

## 3. Search Index Rules

- **Excluded from default local search**:
  - `specs/**` (all feature specs, plans, tasks, checklists, research, contracts)
  - `PLAN.md`, `CHECKLIST.md`
  - `development/DESIGN_AGENTIC.md`, `development/AGENT_TROUBLESHOOTING.md`
- **Primary search weight**:
  - `index.md`, `using-camply.md`, `cli.md`, and `self-hosting/*` appear at full or boosted relevance ahead of `operations/*` and `architecture/*` pages.

## 4. Preserved Routes & Assets

The following paths MUST exist in built `build/docs/` (and bundled `src/camply/server/static/docs/` and `src/frontend/dist/docs/`):

- `/docs/index.html` (with `# Find your next campsite` heading)
- `/docs/using-camply.html` (and `/docs/using-camply/` resolution)
- `/docs/404.html`
- `/docs/assets/camply.svg` (and `/docs/camply.svg`)
