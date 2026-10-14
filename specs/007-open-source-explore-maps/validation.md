# Mapping Implementation Validation

## Environment and Baseline

Validation uses Python 3.12.13, the repository-pinned pnpm/Task workflows, PostgreSQL 17 in a disposable Docker container, and Chromium on an Apple M1/macOS host with the recorded ANGLE/SwiftShader WebGL 2 renderer. All catalog/account fixtures are synthetic. Automation intercepts raster requests; it never crawls public tile servers or reads operator secret files.

- `task install`: passed.
- Baseline `task lint`, `task test`, and `task api:check`: passed (227 frontend tests before changes).
- The initial `task check` ran concurrently with the new geometry red test and reported that intentionally missing module. Subsequent complete backend/frontend checks passed after implementation; this was not recorded as a pre-existing project failure.
- Initial geometry, database-query, Explore-module, and map-route tests were run before those implementations and failed as expected. A dateline marker regression also failed before synchronizing marker world copies on map movement.

## Verified Behavior

- MapLibre GL JS replaces the Google runtime and type dependencies; the initial Leaflet dependency has also been removed. The keyless default and explicit public source/attribution/native-zoom settings apply to all map surfaces.
- Real detail-map tests cover zero coordinates, missing primary coordinates, related markers, cleanup, and stable instances. The dateline regression verifies that neighbors at +179/-179 remain in the same visible world after fitting.
- Database tests preserve current filters and ranking and verify map/list membership parity, missing/invalid coordinates, wrapped/global bounds, co-located groups, cursor traversal, and feature caps at every supported zoom.
- Router tests verify public summary/viewport/members, invalid input rejection, empty success, and cell validation. Generated map DTOs are committed through the existing OpenAPI workflow.
- Frontend tests cover exact provider/ID conversion, campground versus recreation-area actions, off-page selection, member pagination, view/page/history behavior, independent failure states, and current-key query cancellation/stale-response protection.
- The live browser harness proves the entire matching set is discoverable through group/member requests without downloading every list page. It opens real prefilled Monitor forms and both detail pages, tests map failure/retry with a usable list, and checks 375px/1440px light/dark layout overflow.
- A production static build under `/map-check/` verifies a custom local raster source, custom attribution, maximum native zoom, and correct Details/Monitor navigation. An invalid native zoom produces a recoverable map error while list results remain usable.

## Live PostgreSQL Evidence

`task backend:maps:test-postgres` passed against a fresh test-owned container. It exercises 5,000 catalog rows, real fuzzy predicates and window functions, all-results discovery, bounded geographic groups, and complete member cursors. Timing/query-plan evidence is written to `frontend/tmp/maps-postgres.json` and uploaded by CI.

The integration schema is limited to the unchanged Search catalog table. Initial full-metadata creation exposed pre-existing `func.false()`/`func.true()` account defaults that PostgreSQL rejects; account models were left outside this mapping change. No database column, migration, PostGIS extension, cluster cache, or production database is introduced or modified.

## Browser and Performance Evidence

`task maps:verify` passed with the actual API and MapLibre, plus deterministic local raster responses. The final expanded browser run measured:

| Measurement                              | Observed                      | Required  |
| ---------------------------------------- | ----------------------------- | --------- |
| Initial usable map after search response | 403 ms                        | <3,000 ms |
| Group selection feedback                 | 37 ms                         | <500 ms   |
| Group-member loading                     | 103 ms                        | <500 ms   |
| Discovered valid locations               | 4,998 of 4,998                | All       |
| Matching records retained in search      | 5,000, including 2 unmappable | All       |
| Full-world features                      | 265                           | <=512     |
| Largest member page                      | 100                           | <=100     |
| Browser console errors                   | 0                             | 0         |

These are controlled local measurements, not a production latency guarantee. The current browser/version/CPU/fixture and timing details are recorded in `frontend/tmp/maps-browser.json`; the expanded verification includes static subpath/source overrides, invalid-source checks, real touch and keyboard activation, and independent tile/summary/viewport/member recovery. CI retains the generated JSON and browser images.

## Visual Review

The snapshot suite includes 67 scenarios, with 16 map scenarios: Explore, campground, and recreation area at desktop/mobile sizes in both themes, a selected group/member panel, mobile map failure, and collapsed-map desktop/mobile states. Explore and search snapshots show the map stacked above the list without view controls; unrelated snapshot routes remain unchanged.

Review caught transparent tiles under the fixed test clock: Leaflet's clock-based fade animation remained at zero opacity. Disabling tile fade makes the deterministic raster fixtures visible without relying on real-time animation. Baselines were reviewed and regenerated through Task; the final `task snapshot:check` passed. Tile/zoom marker animation is disabled so movement timing does not shift deterministic captures.

## Build and Quality Gates

- `task frontend:build:static`: passed.
- `task frontend:docker`: passed using the existing Compose/Bake workflow and public source build-argument wiring.
- Backend baseline: 532 tests passed, 3 opt-in integrations skipped. The final `task frontend:test` passed all 264 frontend tests; dedicated opt-in map integrations passed separately.
- `task fix`, `task lint`, `task check`, and `task api:check`: passed on the completed implementation, including the keyboard and zero-area viewport regressions.
- `task snapshot:check`: all 67 views passed, including all unchanged non-map routes.
- `task maps:verify`: both the 5,000-row PostgreSQL check and expanded real API/Chromium check passed.
- `task pre-commit -- --all-files`: passed all hooks. The same hooks also passed for every new, untracked file, which `--all-files` does not include before staging.

The all-files hooks exposed two compatibility issues: the token-based docstring hook treats valid module attribute docstrings as duplicate module docstrings, and Oxfmt conflicted with the dedicated TOML formatter. Hook configuration now excludes only the three mapping/search modules using those documented attributes from the token check (AST checks remain), and assigns TOML formatting to its existing dedicated hook. Earlier search-revamp documents now point to the completed mapping follow-up. Unrelated dependency manifests and visual baselines remain unchanged.

## Verification Scope

Chromium and emulated mobile inputs supply automated browser evidence. Firefox, Safari, and physical-device checks are not claimed. Availability scanning, authentication rules, provider ingestion, and account-table compatibility remain governed by their existing suites and architecture; map markers describe catalog locations, not live availability.

## Layout Clarification (2026-10-14)

The map always appears above the result list at every screen size. The List/Map selector is removed; legacy `view` parameters no longer control rendering. Filters, list pagination, sort, and browser history retain their existing behavior. Regression tests first failed on the previous optional-map layout and passed after the change. All 255 frontend tests and frontend type checking passed. The updated isolated live-browser harness passed with the real API, all 4,998 mappable matches reachable, and map/list bounding-box assertions at 375px and 1440px in both themes. It also verified sort/history, unchanged pagination, touch/keyboard actions, failure recovery, and the production subpath build. The initial visual capture showed exactly nine intended Explore/search changes. After review and baseline updates, `task snapshot:check` passed all 65 scenarios; unrelated baselines were retained. Frontend lint and the hooks for every changed source/document also passed.

## Collapsible Map (2026-10-14)

Explore starts with the map expanded above the list. An accessible Show map/Hide map button collapses only the map without changing the URL, filters, or list page. The saved camera updates immediately, independently of debounced viewport requests, so even a recent pan survives collapse/reopen. New filter contexts discard obsolete cameras. All 260 frontend tests passed, including immediate camera saving, restoration only for matching filters, collapse/pagination behavior, and late movement after map removal. The first live-browser run exposed a delayed Leaflet moveend callback reading a removed map; detaching that listener and clearing its instance fixed the reproduced regression. The updated real API/Chromium run then passed collapse/reopen by keyboard at both screen sizes/themes and by touch on mobile, along with the existing discovery, Monitor, history, recovery, and production-subpath flows. It reported zero console errors. Expanded and collapsed snapshots were reviewed; `task snapshot:check` passed all 67 scenarios. Frontend type checking, lint, and pre-commit hooks passed for tracked files and the new feature files. All 53 implementation tasks are complete.

## MapLibre Migration (2026-10-14)

The user selected MapLibre GL JS 6.14.0, replacing the initial Leaflet renderer and type dependency. Public raster settings, keyless OSM tiles, search APIs, grouping, and the collapsible map above the list are retained. The MapLibre style uses one raster source, native controls, and accessible DOM marker buttons. Vite bundles its worker as a same-origin asset. All 264 frontend tests passed, including raster style/settings, safe attribution and referrers, zero/dateline coordinates, saved camera fitting, keyboard buttons, StrictMode cleanup/resize, loading states, unavailable/lost WebGL contexts, and camera-preserving renderer retry. The live API/Chromium harness passed the existing discovery, map/list, touch/keyboard, source override, and static-subpath flows, plus real WebGL disable/restore and context-loss/retry cases. It reached all 4,998 mappable locations and reported zero unexpected console errors. The production worker and raster style also loaded in the static subpath build; Docker build, type checking, and frontend lint passed. Renderer controls/attribution changed 16 intended baselines, and expanded/detail map screenshots were reviewed. `task snapshot:check` passed all 67 scenarios. Pre-commit hooks passed for all tracked files and all new feature files. All 54 implementation tasks are complete. The first browser run identified Vite worker discovery, fixed using MapLibre's documented `?worker&url` integration.

The performance run waits for both markers and the fully loaded renderer/raster style. Initial forced-ANGLE runs exceeded the three-second budget; the final reference uses Chromium's default ANGLE backend with software fallback allowed and records its actual SwiftShader renderer. Timing thresholds remain unchanged. Snapshot browsers explicitly use SwiftShader for deterministic captures. Layout checks read map/list bounds in one frame so removal of a loading status cannot create a false overlap between separate measurements.

## Main Integration and PR Verification (2026-10-14)

Rebased onto current main, retaining live Explore's debounced input, immediate pending-query filter commits, cancellation, safe page parsing, status announcements, and pagination/retry behavior. List and map queries now share the asynchronous PostgreSQL predicate preparation, including the transaction-local word-similarity threshold. Explicit false amenity filters follow current main, and map text inputs use the same 200-character bound. The PostgreSQL map test deliberately changes the session threshold before querying maps first, then verifies typo matching and list parity.

The integrated full suite passed: 549 backend tests and 277 frontend tests, with the normal opt-in integrations skipped. `task search:smoke` passed all nine PostgreSQL migration/index/ranking checks. `task maps:verify` passed both PostgreSQL and real API/Chromium checks. All 4,998 mappable records were reachable with 265 world features and member pages capped at 100; initial usable map was 937 ms, selection 41 ms, and members 109 ms on the controlled local fixture. WebGL recovery, custom source settings, and the production static subpath passed with zero unexpected browser errors.

`task fix`, `task lint`, `task check`, and `task api:check` passed after integration. The targeted router/model regressions passed all 29 tests. `task snapshot:check` passed all 67 views against the reviewed baselines. The all-files hooks passed after formatting the completed snapshot report. All 55 implementation tasks are complete.

## Explore Count Simplification (2026-10-14)

Removed the redundant matching-locations/in-view count above the map. Reviewed and refreshed eight Explore/search baselines; the other 59 views were unchanged. The full suite passed (549 backend and 277 frontend tests), along with lint and type checks.

`task snapshot:check` passed all 67 views against the refreshed baselines. All 56 implementation tasks are complete.
