# Quickstart: Map Implementation Validation

This is the validation guide for the planned implementation. New map endpoints, tests, settings, and Task entrypoints described below must be delivered by the implementation tasks; they are not present in this documentation-only change.

## Prerequisites and Setup

Use Node 24, the repository-pinned pnpm, uv, go-task, and Python 3.12. Docker is required for isolated PostgreSQL verification. Use synthetic fixtures only and avoid existing operator databases or secret files.

From the repository root:

```bash
task install
task frontend:browser:install
```

Follow the normal developer guide for local application startup. For a development instance without proprietary map configuration:

```bash
task dev
```

This should use the default tile source without an account or key. Human viewing may use the public source under its policy; automated verification below intercepts tile requests.

## Focused Automated Verification

After implementing the new tests, run:

```bash
task backend:test -- packages/db/tests/test_search_maps.py packages/backend/tests/routers/test_search.py
task frontend:test -- src/components/MapComponent.test.tsx src/components/ExploreMap.test.tsx src/pages/SearchPage.test.tsx src/hooks/useSearch.test.ts src/lib/maps.test.ts src/lib/api.test.ts
task api:generate
task api:check
```

Expect exact search/map filter parity, coordinate and circular-bounds coverage, bounded viewport results, complete member cursor traversal, stacked map/list layout and URL preservation, correct monitoring selections, isolated failure recovery, and map lifecycle cleanup. Run unchanged legacy search and detail behavior checks alongside these new cases.

## Isolated Database and Browser Verification

Implementation adds `task maps:verify` at the root, following the existing admin smoke-test pattern. It runs a new `backend:maps:test-postgres` task and an opt-in backend integration harness at `packages/backend/tests/integration/test_maps_smoke.py`, which launches `frontend/scripts/verify-maps.ts` against an isolated seeded application. These commands must be wired into CI.

```bash
task maps:verify
```

The PostgreSQL task provisions and removes its own throwaway container/database, enables the existing pg_trgm extension, and uses synthetic fixture credentials passed at runtime. It must not read operator secret files, use an existing application database, or silently skip when PostgreSQL/Docker is unavailable. Apply the project's schema/migrations to this isolated database; exercise real fuzzy predicates, aggregation, and window functions rather than only compiling SQL.

The browser harness starts a temporary application database and backend, loads exactly 5,000 matching synthetic places plus excluded controls, and invokes the existing Vite/Playwright tooling. Intercept all raster requests before page navigation with deterministic image responses. Exercise real frontend requests against the seeded backend; mocked API responses are reserved for targeted error/race cases. Clean up processes, temporary data, and containers on success or failure.

Record browser version, OS/hardware, fixture seed/count, source-response behavior, API/database timings, and browser timings in a verification artifact under `frontend/tmp/` (not a committed baseline). Initial usable map must appear within 3 seconds after the search completes; selected-place and group-expansion feedback must appear within 500ms. Record PostgreSQL query plans and bounded result sizes. Fail acceptance when timing or membership bounds are missed; do not claim success from a mocked renderer alone.

The fixture includes at least three list pages; campground/recreation-area pairs; providers sharing external IDs; missing/invalid/zero coordinates; polar and dateline cases; and more than 100 identical-coordinate locations. Assert total counts and full-world group sums, then traverse member pages to prove every mappable fixture ID is discoverable without fetching all list pages.

## Visual and Manual Scenarios

Extend the existing snapshot runner with path-specific map API mocks and intercepted raster images. Review new desktop/mobile, light/dark map captures and map-error states before updating baselines.

```bash
task snapshot
task snapshot:update
task snapshot:check
```

Run `snapshot:update` only when review confirms the changed baselines are intended.

| Scenario                                           | Expected outcome                                                                                                |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Open campground and recreation-area details        | Primary and related valid locations fit; zero coordinates are retained; attribution is legible                  |
| Open `/search`, change filters                     | Global summary and map use the same filtered set; updated results fit once                                      |
| Hide/reopen the map                                | List stays visible; URL and list page stay unchanged; camera restores for unchanged filters                     |
| Change list page/sort, then pan/zoom               | List presentation changes independently; map extent is not reset and all filtered locations remain discoverable |
| Open a group and Load more                         | More than 100 co-located places remain individually accessible with correct provider/entity labels              |
| Monitor a map place absent from list page one      | Correct provider and campground are preselected; cancel preserves extent and search                             |
| Copy link, reload, back/forward                    | URL filters and list page restore with map above list; visible search input matches URL                         |
| Test at 375px and 1440px in both themes            | No page overflow; map above list with no view selector; controls work by touch and keyboard                     |
| Block tiles, fail summary/viewport/member requests | Separate readable statuses and retry; list Details/Monitor actions remain usable                                |
| Inspect dateline and polar fixtures                | Narrow wrapped bounds and edge markers remain discoverable; no duplicate world-copy actions                     |
| Inspect browser network requests                   | No Google maps runtime, no proprietary map key, no auth/CSRF headers or private scan metadata in tile requests  |

## Alternative Source and Deployment Checks

Use the public settings in [the configuration contract](contracts/map-ui-and-configuration.md). Verify that a custom compatible source changes tiles and linked attribution on all three surfaces. For automated checks, use a local test tile origin and intercept responses; do not automate traffic against public OSM tiles.

Test static and repository-subpath builds, then Docker build-argument forwarding. For example, set the four public VITE_MAP settings in the build process environment with a local fixture URL, synthetic credit, and matching zoom; do not load an operator .env file. Expect malformed config to produce a map-specific error while list search continues. A custom URL without custom attribution must not fall back to misleading default credits.

```bash
task frontend:build:static
task frontend:docker
```

The implementation's new map verification Task must automate source overrides and subpath navigation, including Details links and Monitor. Document the rebuild requirement for changed map settings and the public tile service's capacity policy.

## Final Gates

```bash
task fix
task lint
task check
task test
task api:check
task maps:verify
task snapshot:check
task pre-commit -- --all-files
```

Inspect the final diff after formatters/hooks. Update mapping setup/API/frontend documentation and the global checklist. Detailed implementation checkboxes belong in the future `tasks.md`; this guide does not record unexecuted checks as passed.

Renderer migration checks also cover the bundled MapLibre worker under static subpaths, unavailable WebGL recovery, CORS-enabled raster fixtures, and touch/keyboard DOM markers. Snapshot browsers use deterministic SwiftShader WebGL with local raster responses.
