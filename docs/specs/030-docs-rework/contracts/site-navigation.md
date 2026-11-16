# Contract: Site Navigation, Collapsible Sidebar & Search Hygiene

**Feature**: `030-docs-rework` | **Date**: 2026-11-16

## 1. Top Navigation Bar (`docs/.vitepress/config.ts`)

Top-level navigation MUST present only four concise entries, keeping the primary bar focused on Users and Self-Hosters:

1. `User Guide` → `/using-camply`
2. `CLI` → `/cli`
3. `Self-Hosting` → `/self-hosting/`
4. `Technical` _(dropdown)_:
   - `Architecture & Contributing` → `/technical/`
   - `Technical Reference` → `/reference`

## 2. Unified Collapsible Sidebar (`themeConfig.sidebar`)

All four perspectives remain visible in the shared sidebar, with User Documentation and Self-Hosting expanded by default (`collapsed: false`) and the two technical sections collapsed by default (`collapsed: true`) until opened or navigated to:

| Sidebar Group                 | Default State                 | Items                                                                                                                                                                                                                                                                                                                              |
| ----------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User Documentation**        | Expanded (`collapsed: false`) | `Overview` (`/`), `Web App` (`/using-camply`), `Command Line` (`/cli`)                                                                                                                                                                                                                                                             |
| **Self-Hosting**              | Expanded (`collapsed: false`) | `Overview` (`/self-hosting/`), `Standalone` (`/self-hosting/standalone`), `Docker & Kubernetes` (`/self-hosting/containers`), `Configuration` (`/self-hosting/configuration`), `Maintenance` (`/self-hosting/maintenance`)                                                                                                         |
| **Technical & Architectural** | Collapsed (`collapsed: true`) | `Overview` (`/technical/`), `Contributing` (`/CONTRIBUTING`), `Developer Guide` (`/development/DEVELOPER_GUIDE`), `Style Guide` (`/development/STYLE_GUIDE`), nested `Architecture` group (`Polling Engine`, `Data Model`, `Providers`, `Notifications`, `API & Security`, `Frontend`)                                             |
| **Technical Reference**       | Collapsed (`collapsed: true`) | `Reference Hub` (`/reference`), `Environment Variables` (`/operations/CONFIGURATION`), `Runtime & Packaging` (`/operations/RUNNING`), `Release Operations` (`/operations/RELEASES`), nested `Specs & Planning` group (`Specifications Catalog`, `Roadmap & Plan`, `Feature Checklist`, `Agentic Tooling`, `Agent Troubleshooting`) |

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
