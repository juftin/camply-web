# Implementation Plan: Open-Source Maps & Explore Map View

**Branch**: `unusual-mole` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Feature Directory**: `specs/007-open-source-explore-maps`

**Input**: The mapping specification and the user's confirmation that Explore must cover all filtered results, independently of list pagination.

## Summary

Replace Google Maps with MapLibre GL JS 6.14.0 and a small React lifecycle wrapper shared by existing detail maps and Explore. Use OpenStreetMap raster tiles as the keyless default, with build-time settings for an alternative or self-hosted compatible source and its attribution.

Add public summary, viewport, and group-member search endpoints. PostgreSQL/SQLite queries reuse the exact existing search predicates and aggregate locations into at most 512 geographic cells per viewport. Each group offers a bounded, paginated place picker, so all matching places remain reachable even at identical coordinates. Keep list pagination and sorting independent of map membership.

The design introduces no persistent models, migrations, PostGIS, tile proxy, new worker, or client clustering plugin. It leaves booking providers and availability scanning unchanged.

## Technical Context

**Language/Version**: Existing React 18.3 / TypeScript frontend and Python backend; use Python 3.12 for development while respecting each package's declared compatibility. Root backend metadata currently declares Python >=3.9 and Ruff targets py39; this feature does not change those settings.

**Primary Dependencies**: MapLibre GL JS 6.14.0 with its built-in TypeScript types; existing React Router, TanStack Query, Axios, Shadcn/UI, FastAPI, Pydantic, async SQLAlchemy. Remove `google-map-react`, Leaflet, and their type packages through pnpm.

**Storage**: Existing `Search` catalog rows in PostgreSQL; SQLite remains supported for local development/tests. Filters and list page live in the URL; map extent and selection live in Explore state. The map starts expanded above the list at every width and can collapse without hiding the list. No new persistent storage.

**Testing**: Pytest database/router tests, Vitest/Testing Library lifecycle and interaction tests, Playwright through the existing snapshot runner with intercepted API and tile responses. Add a Task-backed map verification entrypoint for browser interactions, PostgreSQL parity, and the 5,000-place benchmark.

**Target Platform**: Current desktop/mobile browsers, including Chromium, Firefox, and Safari; existing static Vite and Docker deployments, including repository-subpath builds.

**Project Type**: Existing frontend/backend monorepo web application.

**Performance Goals**: Initial usable map within 3 seconds after search completion for 5,000 synthetic matches; location selection/group expansion within 500ms under controlled source responses. At most 512 features per viewport response and 100 members per group request. Measure database execution as well as browser timing; bounded output does not imply constant database work.

**Constraints**: No proprietary key/account requirement; all matching results discoverable; exact filter parity; public catalog-only map data; native browser caching and source attribution; map failures cannot break list search or scanning.

**Scale/Scope**: Three map surfaces, three additive API endpoints, existing Explore filters, global coordinates, mobile/desktop and light/dark validation. A 5,000-place fixture is the acceptance baseline, not a production catalog limit.

## Constitution Check

_Gate checked before research and again after design. These are design checks; implementation quality gates have not run._

| Principle                    | Before research                                       | After design                                                                                                        |
| ---------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Reliability & precision      | Pass: catalog discovery is separate from availability | Pass: markers never claim availability; provider scanning and alerts unchanged                                      |
| Type safety & analysis       | Pass: existing typed boundaries retained              | Pass: Pydantic map DTOs, generated TypeScript aliases, typed MapLibre GL JS integration; lint/type gates required   |
| Modern workflow & automation | Pass: existing Task/uv/pnpm workflows retained        | Pass: validation uses Task; new browser/database verification must have Task entrypoints                            |
| Monorepo boundaries          | Pass: no legacy CLI work                              | Pass: query logic in db, HTTP DTOs/routes in backend, rendering in frontend                                         |
| Automated verification       | Pass: tests planned before application changes        | Pass: synthetic database/API fixtures, browser tile mocks, regressions and measured performance explicitly assigned |

No constitution exception is required. The constitution's older ESLint wording is satisfied through the repository's current Oxlint/Oxfmt Task gates; this feature does not change tooling.

## Project Structure

### Documentation (this feature)

```text
specs/007-open-source-explore-maps/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── search-map-api.md
    └── map-ui-and-configuration.md
```

`tasks.md` is produced by `/speckit.tasks`, after this planning phase.

### Source Code (existing and planned touchpoints)

```text
backend/packages/
├── db/
│   ├── db/models/search.py          # Share existing filter assembly
│   ├── db/search_maps.py            # Bounded map queries (new)
│   └── tests/test_search_maps.py    # Membership, geometry and limits (new)
└── backend/
    ├── backend/routers/search.py    # Three public map endpoints
    ├── backend/schemas.py          # Map response models
    └── tests/routers/test_search.py # Search/map contract regressions
frontend/
├── src/
│   ├── components/MapComponent.tsx # Shared MapLibre GL JS lifecycle and tile states
│   ├── components/ExploreMap.tsx   # React summaries/member picker (new)
│   ├── hooks/useSearch.ts          # Summary/viewport/member queries
│   ├── lib/api.ts                 # Map calls/shared filter serialization
│   ├── lib/maps.ts                # Coordinates/bounds/source config (new)
│   ├── lib/structs.ts             # Generated map type aliases
│   ├── lib/api/generated/schema.ts
│   └── pages/                     # SearchPage/Campground/RecreationArea + tests
├── scripts/run-snapshots.ts       # Deterministic map states
├── scripts/verify-maps.ts         # Browser checks/benchmark (new)
├── Dockerfile                    # Public map build arguments
├── docker-compose.yaml           # Forward public map settings
└── package.json + pnpm-lock.yaml
Taskfile.yaml                      # Aggregate map verification entrypoint
backend/Taskfile.yaml              # Real PostgreSQL verification entrypoint
backend/packages/db/tests/integration/test_search_maps_postgres.py # New
backend/packages/backend/tests/integration/test_maps_smoke.py      # New
frontend/src/index.css             # MapLibre GL JS CSS/shared map styles
.env.example                       # Public build settings documentation
frontend/src/vite-env.d.ts          # Typed public map settings
README.md                          # Mapping setup pointer
.github/workflows/ci.yaml           # Run map verification with isolated fixtures
docs/agents/                       # Setup, API, frontend architecture, checklist
```

**Structure Decision**: Extend the existing search router and predicate assembly. Keep map aggregation in a focused database query module and reuse one MapLibre GL JS component rather than create provider adapters or a second map stack. New helpers exist only for behavior shared across these map surfaces. Deployment files need changes only to wire the documented public settings; unrelated setup is outside scope.

## Phase 0: Research Decisions

Research is complete in [research.md](research.md). MapLibre GL JS, default/configurable raster sources, a portable SQL cell grid, circular longitude bounds, group-member navigation, and integration/testing constraints are resolved. No product clarification remains.

## Phase 1: Design

### Backend and bounded discovery

1. Extract combined attribute/text predicate assembly from `Search.search` without changing matching or ranking. Map queries reuse it with the actual session dialect. Existing flat search and Explore responses remain backward compatible.
2. Summary queries return global filtered counts and the narrowest circular longitude bounds. Sort distinct canonical longitudes in SQL, find the largest gap with window functions, and return the complementary arc; only aggregate results cross into application memory.
3. Viewport queries validate bounds/zoom and group valid locations using a globally aligned latitude/longitude grid. Start at grid level `min(zoom + 2, 20)` and coarsen before querying until the number of intersecting cells is at most 512. Use nonnegative arithmetic and integer casts, avoiding PostGIS and optional SQLite math functions. Aggregate counts/centers in SQL; fetch full metadata only for singleton cells.
4. Groups describe only matching locations inside the requested viewport. Echo that viewport and include it with group-member requests, avoiding mismatched visible group counts and whole-cell membership. Every group supports View places, even if zooming cannot separate its members.
5. Member queries apply the same filters, captured viewport, and grid-cell predicate. Use stable provider-qualified Search IDs for keyset pagination, with 50 items by default and a maximum of 100. Never fetch every list page or maintain a server-side cluster cache.
6. Generate response types using `task api:generate` and gate drift with `task api:check`. Reuse existing search metrics without logging credentials or private data.

Precise shapes, coordinate boundaries, cursors, and errors are in [the API contract](contracts/search-map-api.md) and [data model](data-model.md).

### Frontend and map lifecycle

- Preserve the existing `MapComponent` use sites while extending its input to explicit provider-qualified locations and Explore groups. Correct detail callers' truthiness tests so zero coordinates work. Primary/related marker types are explicit rather than inferred from array order.
- Initialize MapLibre GL JS once per mounted map, update layers when data changes, and remove listeners/layers with `map.remove()` on cleanup. Import MapLibre GL JS CSS and its Vite `?worker&url` worker asset. Use a version-8 raster style, uncollapsed attribution, and origin-only tile referrers. Map-scoped recovery covers unavailable WebGL and renderer errors. Use trusted static marker artwork and React-rendered selected-place/member panels; do not interpolate provider strings into popup HTML.
- Fit detail maps when their locations change. Fit Explore only after a new filter summary, with bounded zoom for single/co-located points. Preserve extent on sort/page changes, and scan-dialog lifecycle. Use `resize()` after resize/reveal; an error boundary around the map subtree preserves list rendering.
- Canonicalize wrapped longitudes for queries and choose the nearest world copy for rendering. Unwrap crossing bounds for MapLibre GL JS fitting. Accept valid polar catalog coordinates and clamp only their displayed projection; extend queries to the corresponding pole when a viewport touches a Mercator edge.
- Use separate TanStack Query keys for summary, viewport, and members, each including canonical filters and excluding sort/page. Pass cancellation signals through Axios; debounce movement by 150ms. Apply responses only to their current key, clear obsolete selection after filter changes, and label retained results as updating.
- Start with the map above the list at every width, with no view selector. Add an accessible Show map/Hide map control that collapses only the map. Store its camera immediately before debounced viewport updates so reopening restores the extent; filter changes invalidate that saved context. Ignore legacy `view` parameters. Preserve list page and filters in the URL and retain map extent during pagination, sorting, and scan dialogs. Browser back/forward must synchronize the displayed search input as well as filters.
- Keep list queries independent of maps. Distinguish summary/viewport errors, tile errors, and initialization errors with individual retry actions. Successful zero counts differ from failed requests. Controls have accessible names; equivalent list actions remain available below the map at every width.
- Reuse one SearchResult-to-Campground conversion for card and map Monitor actions, preserving zero coordinates and exact provider identity. Existing ScanForm access rules remain authoritative.

### Basemap configuration and deployment

Use [the UI/configuration contract](contracts/map-ui-and-configuration.md). The default is OpenStreetMap's HTTPS raster endpoint and linked contributor credit. Build-time overrides cover URL, attribution text/link, and maximum native zoom; changing the source requires rebuilding static assets. Forward settings through Docker and document static-host build settings.

Tile requests use MapLibre GL JS's `referrerPolicy: "strict-origin"`, native browser caching, and no authenticated Axios transport. Add no bulk prefetch, cache-busting retry, tile proxy, geolocation, or offline layer. Document source terms and the IP addresses/tile coordinates visible to external services; self-hosting is the alternative.

### Verification and delivery order

| Slice                  | Evidence required                                                                                                                       |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Detail-map replacement | Coordinate/fit/lifecycle tests; no Google runtime/config dependency; default and override source tests                                  |
| Bounded map API        | Shared-predicate parity; summary bounds/counts; <=512 cells; full member traversal; SQLite and live PostgreSQL coverage                 |
| Explore integration    | All-pages discovery; filter/URL parity; no recenter on pan/page/sort; exact Monitor identity; independent failure recovery              |
| Browser/deployment     | 375px/1440px light/dark coverage; keyboard/touch; real MapLibre GL JS lifecycle; mocked raster requests; static/subpath/Docker settings |
| Final gates            | Measured 5,000-place browser/database runs; Task lint/type/test/API/snapshot checks; docs/checklist updated                             |

Synthetic fixtures cover multiple pages, both entity types, reused external IDs, zero/missing/invalid/polar coordinates, dateline crossings, and more than 100 identical coordinates. Simulate out-of-order responses and independent tile/data failures. Exercise actual PostgreSQL aggregation and fuzzy matching; compiling SQL alone is insufficient.

The existing snapshot runner's broad `**/api/search*` handler can intercept map routes; make dispatch path-specific. Mock raster responses before navigation so automated browsers never pan/zoom against community tile infrastructure. Review visuals before updating baselines. Commands and expected behavior are in [quickstart.md](quickstart.md).

## Risks and Release Checks

- SQL aggregation scans filtered rows and circular bounds require sorting. Benchmark and inspect PostgreSQL query plans before adding indexes or caches. Optimize and remeasure if acceptance timing is missed.
- Separate requests can observe a catalog refresh at different moments. Counts describe each response's current catalog; a detected global count mismatch offers a map refresh. No cross-request snapshot or availability claim is made.
- Public OSM tiles are a best-effort default with usage limits. Document alternative/self-hosted settings; all automated verification uses local tile fixtures.
- Basemap overrides are public build inputs. Verify source/attribution changes in static and Docker builds and confirm removal of Google requests/credentials.

Planning ends here. Application changes and detailed task completion follow `/speckit.tasks`.
