# Research: Open-Source Maps & Explore Discovery

**Date**: 2026-10-13

**Status**: Complete; all planning decisions resolved.

## 1. Renderer and React Integration

**Decision (updated 2026-10-14)**: The user selected MapLibre GL JS. Use its built-in TypeScript types and a shared React lifecycle wrapper. Replace Leaflet through pnpm. Keep the existing keyless OpenStreetMap raster XYZ source and four public build settings, expressed as a MapLibre version-8 style with a raster source/layer. The map APIs and server grouping remain unchanged.

**Rationale**: MapLibre supports the existing discovery behavior and provides a path to vector styles and richer geographic presentation. This migration changes the renderer; it does not add an unrequested tile-hosting service, vector-data dependency, terrain layer, or configuration surface. Use native MapLibre controls, accessible DOM marker buttons, React summaries, and explicit resource cleanup on collapse/unmount. The map starts expanded above the list and remains collapsible.

**Alternatives considered**: Leaflet was initially selected for the raster/marker scope. That selection is superseded by the user's preference. OpenLayers offers broader GIS/data-service capabilities that this feature does not currently require. No comparative performance benchmark is claimed.

**Sources**: [MapLibre raster-source example](https://maplibre.org/maplibre-gl-js/docs/examples/add-a-raster-tile-source/), [MapLibre lifecycle](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/), [MapLibre request parameters](https://maplibre.org/maplibre-gl-js/docs/API/type-aliases/RequestParameters/), [OpenLayers overview](https://openlayers.org/).

## 2. Default Basemap, Configuration, and Requests

**Decision**: Default to `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, maximum native zoom 19, and linked OpenStreetMap contributor attribution. Support compatible alternative/self-hosted raster XYZ sources through public build-time URL, attribution text/link, and native-zoom settings.

**Rationale**: This supplies a working keyless baseline while keeping the map software independent of hosting. Open map data and open-source software do not confer unlimited use of a community tile service. The public default is best effort; production operators can select an appropriate source.

Use native browser caching, origin-only HTTPS referrers, and MapLibre-managed raster requests. Do not send application authorization/CSRF headers through the API client to tile hosts. Retry redraws through ordinary cache behavior, without query-string cache busting. No bulk/offline tile prefetch is added. Tests intercept tile requests. External sources observe client IP addresses and requested tile coordinates; document this and the self-hosting option.

**Alternatives considered**: Requiring an account-backed tile service would defeat the keyless default. Shipping a tile server or proxy would introduce new infrastructure outside scope. A runtime settings endpoint would add a deployment mechanism absent from current frontend map configuration; use existing Vite build conventions.

**Sources**: [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/), [OSM copyright and data license](https://www.openstreetmap.org/copyright), [MapLibre raster example](https://maplibre.org/maplibre-gl-js/docs/examples/add-a-raster-tile-source/).

## 3. All-Results Discovery With Bounded Responses

**Decision**: Separate global search summary, viewport features, and paginated group members. Aggregate a deterministic geographic grid in SQL; choose a grid level whose intersecting-cell count is at most 512 before executing the grouped query. Groups always expose a member picker, including below maximum zoom.

**Rationale**: The user explicitly selected all filtered results. Current Explore returns 20 items per page, capped at 100. Fetching all pages or sending every matching row would violate the bounded-discovery requirement. SQL aggregation works with the existing PostgreSQL and SQLite storage and needs no shared cluster cache, PostGIS, or new worker. A member picker solves identical-coordinate overlap without spiderfying markers or requiring impossible extra zoom.

**Alternatives considered**: Page-only markers are explicitly rejected by the user. Fetch-all plus browser clustering has unbounded transfer. Supercluster on the server requires constructing/caching a full index and keeping cluster IDs in sync with catalog changes; that lifecycle is unnecessary here. PostGIS would change local infrastructure and testing for a feature satisfiable with existing coordinate fields.

**Repository evidence**: `backend/packages/db/db/models/search.py` stores nullable coordinate floats and already builds attribute and dialect-specific text predicates. `backend/packages/backend/backend/routers/search.py` exposes paginated `/search/explore`. Share the existing combined predicates; do not copy approximate matching into a new router.

## 4. Filter Semantics and Identity

**Decision**: Extract current predicate assembly once and reuse it for list, summary, viewport, and members. Keep explicit provider/entity/external-ID fields in every actionable item; use the existing qualified Search primary key for deterministic member pagination.

**Rationale**: PostgreSQL fuzzy matching and SQLite substring matching differ by design. Existing behavior also makes `q` override `query`, including an empty `q`; explicit true/false electric/pets values constrain the matching boolean, nonpositive RV length adds no constraint, and radius filtering uses the existing approximate box. The map must preserve those behaviors. Pagination and sorting never enter map membership keys.

Map groups count only locations inside their returned viewport. Member requests include the original viewport as well as the cell ID, preventing a partially visible cell from returning more members than its displayed count. Provider IDs and entity types distinguish reused external IDs; never derive navigation from a display label or parse Search IDs into booking IDs.

## 5. Coordinates, World Wrapping, and Bounds

**Decision**: Validate finite geographic ranges, canonicalize longitude 180 to -180 for indexing, use half-open grid cells with an explicit north-pole rule, and retain original coordinates in place metadata. Use SQL window functions over distinct longitudes to find the largest circular gap; the complementary arc supplies narrow global bounds. Crossing bounds use `west > east`.

**Rationale**: Zero is valid and the current detail pages and SearchPage conversion incorrectly use truthiness. Ordinary longitude min/max would frame dateline neighbors as almost a whole world. Window functions let the database return the compact aggregate without loading the coordinate catalog into Python. Positive-domain arithmetic plus integer casts avoids optional SQLite floor functions.

The default Web Mercator projection cannot display the geographic poles at their literal latitude. Clamp only the display projection to approximately ±85.05112878°, retain the original coordinate values, and extend edge viewport queries to ±90° so valid polar catalog entries stay reachable.

**Sources**: [PostgreSQL window functions](https://www.postgresql.org/docs/current/functions-window.html), [SQLite window functions](https://www.sqlite.org/windowfunctions.html), [MapLibre geographic bounds](https://maplibre.org/maplibre-gl-js/docs/API/classes/LngLatBounds/), [MapLibre Mercator coordinates](https://maplibre.org/maplibre-gl-js/docs/API/classes/MercatorCoordinate/).

## 6. Accessibility, State, and Verification

**Decision**: Keep a stable MapLibre instance with explicit cleanup, accessible marker names, React panels, equivalent list actions, and independently recoverable tile/data errors. Following the 2026-10-14 UI clarification, start with the map above the list with no view selector, and provide a Show map/Hide map control that leaves the list available. Keep filters and list page in the URL and preserve extent in parent state. Legacy `view` parameters do not control rendering.

**Rationale**: Existing `SearchPage.updateParams` resets page for every non-page update, and its local input does not synchronize on back/forward navigation. Both need focused changes. The existing snapshot runner registers a broad search interceptor, which must not shadow new map routes. Real MapLibre browser tests complement mocked unit tests; actual PostgreSQL checks complement SQLite tests.

**Source**: [MapLibre marker API](https://maplibre.org/maplibre-gl-js/docs/API/classes/Marker/), [MapLibre lifecycle and events](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/).

## Research Outcome

No unresolved clarification remains. Production tile capacity and achieved query/browser timing are implementation validation items, with explicit alternatives and acceptance gates; they do not require a new product decision.
