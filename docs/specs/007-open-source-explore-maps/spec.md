# Feature Specification: Open-Source Maps & Explore Map View

**Feature Branch**: `unusual-mole`

**Feature Directory**: `specs/007-open-source-explore-maps`

**Created**: 2026-10-13

**Status**: Implemented; verification recorded in [validation.md](validation.md).

**Input**: User description: "Let's create a spec-kit spec for replacing our mapping provider for something open source - I'd also like to create a map view in the Explore page."

## Clarifications

### Session 2026-10-13

- Q: Should Explore's map show all filtered results or only the current list page? → A: All matching results, independent of list pagination.

### Session 2026-10-14

- Q: Should visitors choose between List and Map? → A: Show both, with the map above the list at every screen size; remove the view selector.
- Q: Which renderer should the implementation use? → A: MapLibre GL JS.
- Q: Should the map be collapsible? → A: Yes. Start expanded, allow hiding/showing the map, keep the list visible, and preserve the map extent when reopened.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Use Existing Maps Without a Proprietary Provider (Priority: P1)

As a camper or self-hosting operator, I want campground and recreation-area maps to use open-source mapping without requiring a proprietary mapping account or API key, so that maps work in a standard installation.

**Why this priority**: Replacing the existing mapping dependency delivers immediate value on both detail pages and establishes consistent mapping for Explore.

**Independent Test**: Start an installation without proprietary mapping credentials, visit a campground and a recreation area, and verify their locations, related campground markers, pan/zoom controls, and attribution.

**Acceptance Scenarios**:

1. **Given** an installation with no proprietary mapping account or credentials, **When** a visitor opens either detail page with valid coordinates, **Then** an interactive basemap and the primary location are displayed without an account or key prompt.
2. **Given** a recreation area or campground with related campgrounds, **When** its map opens, **Then** the initial extent includes the primary location and related locations with valid coordinates, and labels distinguish the primary location from related campgrounds.
3. **Given** an operator has configured a supported alternative or self-hosted basemap source and its attribution, **When** a visitor opens any map, **Then** that source and attribution are used consistently.
4. **Given** a primary location has no usable coordinates, **When** its detail page opens, **Then** the location is not plotted at an invented position and the remaining detail content stays usable.

---

### User Story 2 - Discover All Matching Places on Explore's Map (Priority: P1)

As a camper exploring an unfamiliar region, I want to see where all places matching my search are located, so that I can compare options geographically without paging through a list.

**Why this priority**: Geographic discovery is the requested new Explore capability; a map limited to one list page would hide relevant places.

**Independent Test**: Search a synthetic catalog spanning multiple list pages and regions. Inspect map locations absent from page one, change filters, and verify that every matching place with valid coordinates remains discoverable.

**Acceptance Scenarios**:

1. **Given** a search has more matching locations than fit on one list page, **When** a visitor opens Explore, **Then** all matching locations with valid coordinates are represented individually or in explorable groups, including locations outside the current list page.
2. **Given** Explore's map is visible, **When** the visitor changes the search text, state, or an existing amenity or RV-length filter, **Then** the map updates to the same matching set as the list and initially frames the updated mappable results.
3. **Given** the map represents the filtered set, **When** the visitor changes list page or sort order, **Then** map membership is unchanged.
4. **Given** many locations overlap or lie close together, **When** the visitor selects a group or zooms in, **Then** they can reach each location; locations sharing exactly the same coordinates remain individually selectable.
5. **Given** the visitor pans or zooms, **When** the visible area changes, **Then** the map reveals matching locations in that area without changing the list's filters, total, or current page, and without immediately resetting the chosen extent.
6. **Given** matching places lack usable coordinates, **When** results load, **Then** those places remain in the list and total, and the interface explains how many matching places cannot be mapped.
7. **Given** a previous search is still loading when a new search begins, **When** responses arrive out of order, **Then** the settled map and list represent the latest search and any retained earlier data is identified as updating.

---

### User Story 3 - Inspect a Place and Start Monitoring (Priority: P2)

As a camper who finds a promising map location, I want its name, provider, type, and relevant actions, so that I can open its details or configure a scan without repeating my search.

**Why this priority**: Map discovery becomes useful when it connects to the existing campground details and monitoring journey.

**Independent Test**: Select campground and recreation-area locations, including results outside the current list page and providers sharing the same external ID. Verify destinations and monitoring selections.

**Acceptance Scenarios**:

1. **Given** a campground location is selected, **When** its summary opens, **Then** it shows the campground name, provider, entity type, available region information, a Details link, and a Monitor action.
2. **Given** a campground summary is open, **When** the visitor selects Monitor, **Then** the existing scan form opens with that exact provider and campground selected and existing authentication, invitation, and scanning-access rules apply.
3. **Given** a recreation-area location is selected, **When** its summary opens, **Then** it identifies the recreation area and links to its details without offering a campground scan for the area itself.
4. **Given** different providers reuse a location ID, **When** either location is selected, **Then** its summary, details destination, and monitoring selection identify the correct provider and entity.
5. **Given** the scan form is open, **When** the visitor cancels or closes it, **Then** Explore retains the search, filters, list page, and map extent.

---

### User Story 4 - Explore on Mobile and Recover From Map Failures (Priority: P2)

As a visitor on a phone, using a keyboard, or experiencing a map outage, I want understandable controls and a usable list alternative, so that I can continue discovering and monitoring campgrounds.

**Why this priority**: The map must work within the existing mobile-first experience and must not make search depend on basemap availability.

**Independent Test**: Exercise Explore at mobile and desktop widths, in light and dark themes, using keyboard navigation and simulated basemap and map-results failures.

**Acceptance Scenarios**:

1. **Given** a desktop viewport, **When** the visitor opens Explore, **Then** the map appears above the result list, both remain usable, and search and filters stay accessible.
2. **Given** a mobile viewport, **When** the visitor opens Explore, **Then** the map and list initially appear together in a vertical stack that fits the screen without a view selector; Show map/Hide map collapses only the map.
3. **Given** an Explore link includes search filters and a list page, **When** it is reloaded or opened in another browser, **Then** Explore restores those parameters with the map initially expanded above the list; browser back/forward restores them while retaining the local collapse state.
4. **Given** a map cannot initialize, load its basemap, or load matching locations, **When** the failure occurs, **Then** a readable map-specific status and retry action appear while the list, details links, and existing monitoring flow remain usable.
5. **Given** keyboard navigation or a light/dark theme, **When** the visitor uses filters, location summaries, or recovery actions, **Then** controls have accessible names, visible focus, readable content, and no keyboard trap; the list provides equivalent Details and Monitor actions.

### Edge Cases

- No matching results: show the existing empty search state and no stale locations.
- Matches exist but none are mappable: show an explicit no-locations state and retain every match in the list.
- Exactly one mappable result: center it at a useful bounded zoom rather than zooming indefinitely.
- Missing, non-finite, or out-of-range coordinates: omit the location from the map. Latitude or longitude equal to zero is valid; do not discard it through truthiness checks.
- Sparse worldwide results, including locations across the antimeridian: frame them without assuming all providers are in the continental United States.
- Dense or identical coordinates: keep individual locations reachable without requiring impossible additional zoom.
- A broad search exceeds the map's display capacity: represent results in explorable groups or clearly identify a partial view and how to reveal the remaining results; never silently present an arbitrary subset as complete.
- A selected place no longer matches after a filter change: dismiss the obsolete selection and its actions.
- Tile loading fails while location data succeeds, or vice versa: distinguish the failure from an empty search and allow retry without clearing filters.
- Filter changes, browser navigation, and container resizing: retain valid state and render the map at the correct size.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: All existing campground and recreation-area maps and the new Explore map MUST use open-source mapping software and support a default setup requiring no proprietary mapping account, API key, or paid subscription. The replacement MUST remove the Google Maps runtime dependency and its required configuration from the supported web application setup. (Story 1)
- **FR-002**: Operators MUST be able to configure the basemap source and required attribution, including a compatible self-hosted source. Setup documentation MUST distinguish software licensing, map-data licensing, and tile-service usage limits and hosting costs. The default MUST follow the selected service's published usage policy. (Story 1)
- **FR-003**: Every map MUST display legible, linked attribution required by its configured source at desktop and mobile sizes. (Stories 1, 4)
- **FR-004**: Detail maps MUST preserve the primary location, related campground locations, labels, and pan/zoom behavior, and initially fit all valid locations. Invalid primary coordinates MUST NOT prevent the rest of the detail page from rendering. (Story 1)
- **FR-005**: Explore MUST initially show both the map and result list in a vertical stack, with the map above the list at desktop and mobile widths. The map MUST be collapsible through an accessible Show map/Hide map control while the list stays visible; reopening MUST restore its extent for the current filters. It MUST NOT offer a List/Map selector or require a view parameter. Existing search links, including legacy view parameters, MUST remain usable. (Stories 2, 4)
- **FR-006**: Explore's map MUST represent all matching mappable campgrounds and recreation areas across every list page. Every such place MUST be individually discoverable, including from dense groups; the current list page MUST NOT determine map membership. (Story 2)
- **FR-007**: Map and list MUST apply identical existing search and filter semantics. Changing filters MUST refresh both, reset list pagination as it does today, and fit the updated mappable set. List sorting and pagination MUST NOT alter map membership. (Story 2)
- **FR-008**: Map data transfer and rendering MUST remain bounded for broad searches without downloading every list page. Grouping, loading only relevant areas, or equivalent behavior MUST preserve access to all matches. Any incomplete representation MUST be visibly identified with a way to discover remaining matches. (Story 2)
- **FR-009**: Panning or zooming MUST affect only map exploration in this release. It MUST NOT implicitly filter the list or repeatedly recenter the map. Collapsing/reopening the map or dismissing a scan form MUST preserve the current map extent while Explore remains open. (Stories 2, 3, 4)
- **FR-010**: Explore MUST persist existing search filters and list page in a shareable page address and restore them on reload and browser back/forward navigation, with the list available whether the map is expanded or collapsed. Existing search links MUST remain valid. (Story 4)
- **FR-011**: Each selected location MUST identify its name, provider, entity type, and available region information and offer its correct Details destination. Campground locations MUST also offer the existing Monitor flow with the exact campground and provider preselected, subject to existing access controls. Recreation areas MUST NOT be submitted as campgrounds. (Story 3)
- **FR-012**: Map locations and selections MUST be distinguished by provider, entity type, and external identifier. Locations sharing coordinates or external IDs MUST NOT overwrite one another. A selection that no longer matches MUST be cleared. (Stories 2, 3)
- **FR-013**: Only finite coordinates within latitude [-90, 90] and longitude [-180, 180] MUST be plotted; zero values MUST be accepted. Missing or invalid coordinates MUST NOT remove otherwise matching places from the list or totals. Explore MUST report the number of matches without mappable coordinates. (Stories 1, 2)
- **FR-014**: Explore MUST distinguish initial loading, updating, no matches, no mappable matches, basemap failure, and map-results failure. Map failures MUST provide retry and preserve list access; superseded search responses MUST NOT replace the current results. (Stories 2, 4)
- **FR-015**: Map controls, summaries, and attribution MUST remain readable in light/dark themes and usable by touch and keyboard. All discovery actions MUST also be available through the list so that interaction with the map is not required to open details or start monitoring. (Story 4)
- **FR-016**: Mapping MUST use existing catalog coordinates and public place metadata. Loading maps MUST NOT require device geolocation or send account credentials, scan settings, or private user information to mapping services. (Stories 1–4)

### Key Entities

- **Search context**: The existing text query, location and amenity filters, sort order, and list page. Filters determine the matching set; sort and page determine only list presentation.
- **Map location**: A matching campground or recreation area with valid coordinates, provider-qualified identity, display metadata, and permitted discovery actions.
- **Map group**: A navigable representation of multiple matching locations with a count and a way to reach each member, including co-located places.
- **Map view state**: The visible extent and selected location, which need only persist during the current Explore visit. The map starts expanded above the always-visible list. Its expanded/collapsed state and extent persist during the current Explore visit; filters and list page remain shareable.
- **Basemap configuration**: An operator-selected map source and its attribution, independent of campsite booking providers and availability data.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: On a clean installation with no proprietary mapping credentials, all three map surfaces—campground detail, recreation-area detail, and Explore—display an interactive map with required attribution.
- **SC-002**: For a synthetic search spanning at least three list pages, 100% of matching places with valid coordinates can be reached on the map regardless of the current list page; 100% of places without valid coordinates remain accessible in the list.
- **SC-003**: For each existing Explore filter and each tested combination, mapped places match the same filtered set as the list. Pagination, sorting, and panning introduce zero unintended membership changes.
- **SC-004**: From any selected campground, a visitor can open its correctly prefilled monitoring form in one action. Tests with overlapping external IDs produce zero incorrect provider or campground selections.
- **SC-005**: At 375px and 1440px viewport widths, in light and dark themes, visitors can use the map above the list, change filters, open details, and start monitoring without horizontal page overflow or a keyboard trap.
- **SC-006**: Under simulated basemap and map-results outages, 100% of the list-based search, details, and monitoring acceptance flows remain usable, and retry does not clear the current search.
- **SC-007**: With 5,000 synthetic matching places and controlled successful map-source responses, Explore presents its initial usable map representation within 3 seconds after search completion; location selection and group expansion respond within 500 milliseconds on the documented reference desktop browser. The validation records the browser, hardware, and fixture used.
- **SC-008**: Reloading a copied Explore link and using browser back/forward restore filters and list page while preserving the local collapse state during the visit in every navigation acceptance case.

## Assumptions

- Explore refers to the existing public `/search` page, currently a paginated list of campgrounds and recreation areas. This feature completes the map-discovery intent in [the search revamp spec](../004-search-revamp/spec.md).
- The user confirmed that map discovery must cover all filtered matches. This requires a map-oriented representation beyond the current paginated list response; its contract and loading strategy belong in the implementation plan.
- Open-source mapping means an open-source renderer with openly licensed basemap data and a keyless default. It does not promise free or unlimited third-party tile hosting. Operators may choose compatible hosted or self-hosted sources.
- The user selected [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/) for the renderer. The default remains keyless OpenStreetMap raster tiles; the implementation keeps alternative/self-hosted raster configuration. Vector basemap styles and terrain are possible future extensions, outside this renderer migration.
- If the default uses OpenStreetMap's public tile service, deployment must follow its [tile usage policy](https://operations.osmfoundation.org/policies/tiles/), which specifies attribution and caching requirements and offers no availability guarantee. Production documentation must describe an alternative source or self-hosting path.
- Catalog metadata supplies coordinates; this feature does not repair provider metadata, geocode missing locations, or change availability accuracy. A marker indicates a catalog location, not current campsite availability.
- Existing scan creation, authentication, invitation, and suspension behavior is reused. New booking providers, date/availability map layers, routing, satellite imagery, offline downloads, device geolocation, and a new tile-hosting service are outside scope.
- The [technical plan](plan.md), [implementation tasks](tasks.md), and [validation evidence](validation.md) record the completed Spec-Kit implementation phases.
