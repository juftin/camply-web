# Frontend Architecture

The web client lives in `src/frontend/` and uses React 18, TypeScript, Vite 8, Tailwind CSS, Shadcn/UI primitives, TanStack Query, React Hook Form + Zod, and MapLibre GL JS.

## Key application journeys

- **Explore (`/search`):** Stacks an interactive MapLibre map above a paginated list with amenity, ADA, and minimum RV-length filters. Panning or zooming debounces viewport bounds (`west`, `south`, `east`, `north`, `zoom`) to filter results in sync; an optional `Show map` / `Hide map` toggle preserves camera extent during the session. Initial unfiltered visits center roughly via `ipapi.co` (coordinates cached in memory, 2.5s timeout) without prompting for browser location.
- **Destination details:** Campground and recreation-area pages display cached photos in an Embla carousel, an overview map, and "Know before you go" practical details without triggering live upstream enrichment requests.
- **Dashboard & scan management (`/dashboard`, `/dashboard/scans/:scanId`):** Groups scans by destination, supports creation/editing (`ScanForm`) with campground or recreation-area coverage (`all` vs. `selected`), site preferences (type, electric, ADA accessibility, minimum RV length `1–200` ft), `Weekends` / individual-night selectors, and presents matching openings in `FoundCampsites` via an interactive availability calendar paired with deduplicated campsite cards (10 sites per page, vehicle-length and equipment badges, inline stay-chip expansion) plus a Sites × Dates availability grid view with inline stay inspection and a consolidated scan detail header with structured recreation-area coverage (`CoverageSummary`).
- **Admin (`/admin/*`):** Provides KPI overview, user/scan management, access-request review, worker operations, audit log inspection, and Recharts metric trends (`AdminTrendsPanel`).

## Key source layout

| Path                                   | Responsibility                                                                                  |
| -------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `src/frontend/main.tsx`, `App.tsx`     | Root providers (`QueryClientProvider`, `AuthProvider`, `ThemeProvider`) and React Router routes |
| `src/frontend/lib/api/`                | Axios API client, helpers, and OpenAPI-generated TypeScript schema (`task api:generate`)        |
| `src/frontend/hooks/`                  | `useAuth`, `useScans`, `useSearch`, `useProviders`, and admin query hooks                       |
| `src/frontend/components/ScanForm.tsx` | Scan creation/editing dialog with Zod validation and weekday/coverage/equipment pickers         |
| `src/frontend/components/Map*.tsx`     | MapLibre GL JS integration and viewport-driven explore markers                                  |
| `src/frontend/public/branding/`        | Light/dark outlined SVG brand marks (`CamplyLogo`)                                              |

## Build and docs bundling

Production frontend builds (`vite build`) compile VitePress docs under `docs/` and copy them into `dist/docs/` alongside the SPA bundle. In Python distributions, the Hatchling build hook embeds `build/frontend/` into `camply/server/static/` without staging generated files into Git-tracked source.

Public map tile overrides (`VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_*`) are build-time environment variables documented in [Environment Variables](../operations/CONFIGURATION.md).

## Responsive layout

The sticky header switches from a Radix `Sheet` navigation drawer below 768 px to inline navigation at 768 px. The drawer traps focus, restores it to the menu button, and closes on navigation, Escape, or a backdrop click.

Multi-field dialogs bound their height to the dynamic viewport. `DialogBody` scrolls between the header and actions. Date and campground pickers expand in the form flow on phones so their controls remain reachable inside that scroll area. The date picker limits its width to the available space, and form inputs and native selectors use at least 16 px type on phones to avoid Safari focus zoom.

Admin Users, Invitations, and Scans render stacked cards below 768 px and tables at wider widths. Operational, trend, audit, and detail tables scroll inside their own containers. The Playwright snapshot runner checks document width for mobile capture states and sweeps all 26 production routes at 375, 390, and 768 px.
