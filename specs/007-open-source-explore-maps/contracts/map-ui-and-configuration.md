# Contract: Map UI and Basemap Configuration

## URL and Layout

- Every `/search` page initially displays both map and list. A Show map/Hide map button with `aria-expanded` and `aria-controls` collapses only the map; the list remains available. Collapse state is local to the current Explore visit. There is no view selector or required view parameter; legacy `view` values do not affect the layout.
- Query text, state, electric/pets/RV filters, sort, and list page retain their current names and behavior. Filter changes continue resetting page.
- At every width, the expanded map appears above the usable result list in a vertical stack; filters remain accessible. Validate at 375px and 1440px.
- Filters and list page survive reload/shared links and browser back/forward, with the list available whether the map is expanded or collapsed. Extent need only survive the current Explore visit and must survive collapse/reopen for unchanged filters. Save the camera immediately on movement; debounce only viewport requests. Changing filters while collapsed must fit the new matching set when reopened. Selection is ephemeral.
- Opening Explore first fits the global filtered mappable bounds. Later fits occur only on filter changes; pan/zoom, list page/sort, scan dialog opening/closing, and resize do not trigger a fresh global fit.
- Display total matches and unmappable matches from summary, and label visible represented matches separately. Group counts count places, not available campsites.

## Locations, Groups, and Actions

- Distinguish campgrounds, recreation areas, primary detail locations, and related detail locations through icons/labels rather than color alone.
- A selected location opens a React-rendered summary with name, provider, entity type, available region information, and Details. Campgrounds also expose Monitor with exact provider and campground selected. Recreation areas link only to their own details.
- Groups show counts and offer Zoom in plus View places. At maximum zoom or degenerate bounds, focus the member picker instead of repeatedly attempting to zoom. The picker uses the API's bounded pages, exposes Load more, and retains previously loaded members for that selection.
- An API item outside the current list page is fully actionable from its summary or the group picker. Reuse the card's scan form and conversion logic; use nullish handling for zero coordinates.
- Use static trusted marker markup or DOM nodes with textContent. Never interpolate catalog names/labels into MapLibre GL JS HTML. React supplies dynamic panels and ordinary router links, including base-path handling.
- Markers/groups and controls have accessible names, keyboard activation, visible focus, and no traps. Move focus into a keyboard-opened panel and return it on dismissal. The list exposes equivalent Details/Monitor actions in both themes.

## Lifecycle, Coordinates, and Recovery

- Use one MapLibre GL JS instance per mounted map; initialize in an effect, remove on cleanup, and tolerate React StrictMode remounts. Update layers without resetting extent. Invalidate size after reveal/container changes.
- Use a default single-point zoom of 12 and map maximum zoom 19. Fit multi-point bounds with padding and maxZoom=12 initially. Group zoom actions may progress to 19. Display valid polar coordinates at the Mercator edge while retaining original metadata and expanding edge queries to include the poles.
- Tile loading uses MapLibre GL JS directly, separately from authenticated Axios requests. Set `referrerPolicy: "strict-origin"` on the tile layer. Keep native browser cache headers and HTTPS-origin referrers; do not use no-referrer on these requests or append cache-busting retries.
- Initial loading, updating, successful no matches, successful no mappable matches, tile errors, map-data errors, member errors, and initialization errors are distinct states. A tile error is a nonblocking map warning; data failures never masquerade as empty results. Offer retry without clearing search, filters, list page, or extent.
- Scope the error boundary to the map. Re-render/retry initialization without unmounting the list or scan form. Keep list queries independent and available even when all mapping requests fail.
- Use query keys/current-context guards and request cancellation to prevent stale response replacement. Cancel or discard obsolete member requests when selection or filters change. Retained previous results are labeled Updating until the current response succeeds.

## Public Build-Time Settings

These values are public frontend configuration. Do not place secrets in them. Use Vite conventions for static builds; forward matching build args through Docker/Compose. A change requires rebuilding the frontend; no runtime configuration endpoint is introduced.

| Setting                   | Default                                        | Purpose                                         |
| ------------------------- | ---------------------------------------------- | ----------------------------------------------- |
| VITE_MAP_TILE_URL         | https://tile.openstreetmap.org/{z}/{x}/{y}.png | Compatible 256px raster XYZ tiles in EPSG:3857  |
| VITE_MAP_ATTRIBUTION_TEXT | © OpenStreetMap contributors                   | Plain-text contributor credit                   |
| VITE_MAP_ATTRIBUTION_URL  | https://www.openstreetmap.org/copyright        | Linked credit/license page                      |
| VITE_MAP_MAX_NATIVE_ZOOM  | 19                                             | Source's highest native tile zoom, integer 0–19 |

MapLibre GL JS may overzoom from the native maximum up to map zoom 19. Attribution uses a DOM link with textContent and a validated HTTPS URL, alongside MapLibre GL JS's built-in software credit. Sources requiring multiple credits can link their full attribution page with the required combined plain-text credit; verify that the selected service permits this presentation.

Supported tile templates use `{z}`, `{x}`, `{y}` without subdomain requirements and are HTTPS URLs or same-origin root-relative paths. Resolve relative paths against the deployed origin. Reject unsupported schemes, missing template tokens, invalid attribution links, and invalid zoom values with an explicit map-configuration error that preserves the list. A custom URL requires explicit custom attribution text/link; never silently attach OSM's default credit to an unrelated source.

No changes are required for the default. To use a self-hosted compatible source, build with the four public values set to that source's URL, credit text/link, and supported zoom. Update `.env.example`, deployment docs, and Docker wiring during implementation; do not read or modify operator secret files.

The old `VITE_GOOGLE_MAPS_API_KEY` setting and Google package dependencies are removed from supported web setup. No replacement proprietary key is required. Tile requests do not use the application Axios instance or attach account authorization/CSRF headers. Deployment documentation must state that external tile services receive IP addresses and requested areas, and describe self-hosting as the alternative.

## Tile-Service Policy

For the default, follow [the OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/): visible linked attribution, valid HTTPS referrers, ordinary browser caching, no bulk downloads/offline features, and no automated tile crawling. The service offers no SLA; an alternative/self-hosted compatible source is the production capacity path. Software licensing, data licensing, tile-service limits, and hosting costs must remain distinct in setup documentation.

Browser tests, screenshots, and benchmarks must intercept raster tile requests before navigation and use deterministic local fixtures. Verification must not generate traffic against public OSM tiles.

MapLibre GL JS uses a bundled same-origin worker and requires WebGL 2. Unavailable graphics contexts and worker/renderer failures must stay within the map error/retry flow. Cross-origin raster sources must allow CORS; tile requests use the configured origin-only referrer policy and ordinary browser caching.
