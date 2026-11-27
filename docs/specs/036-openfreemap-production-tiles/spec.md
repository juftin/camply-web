# Feature Specification: OpenFreeMap Production Map Tiles

**Feature Branch**: `openfreemap-production-tiles`

**Feature Directory**: `docs/specs/036-openfreemap-production-tiles`

**Created**: 2026-11-27

**Status**: Draft

**Input**: Phase 3 (`T3.3.6`): Replace OpenStreetMap's public raster tile server as the default production basemap with OpenFreeMap vector map styles at $0/month with zero additional infrastructure, while preserving full backwards compatibility with custom raster tile overrides and deterministic offline-safe automated verification.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Production-Ready Default Maps via OpenFreeMap Without Extra Infrastructure (Priority: P1)

As a camper browsing campgrounds or a self-hosting operator deploying camply, I want every interactive map (Explore, Campground detail, and Recreation Area detail) to use OpenFreeMap's free, open-source vector basemap by default with no API keys, accounts, or proxy servers required, so that public and self-hosted production deployments comply with OpenStreetMap's Tile Usage Policy at zero hosting cost.

**Why this priority**: Relying on OpenStreetMap's public raster tile server (`tile.openstreetmap.org`) as the default violates OpenStreetMap's Tile Usage Policy for production and high-traffic deployments. Switching the built-in default to OpenFreeMap immediately makes every standard deployment—hosted, self-hosted container, and standalone package—production-ready out of the box without adding infrastructure or billing accounts.

**Independent Test**: Build and launch the application with no basemap environment overrides configured. Open Explore, a Campground detail page, and a Recreation Area detail page. Verify that maps load OpenFreeMap's default vector style, display crisp cartography across zoom levels up to maximum zoom, show the style's required attribution links, and make zero requests to `tile.openstreetmap.org`.

**Acceptance Scenarios**:

1. **Given** an installation built with no custom basemap settings, **When** a visitor opens Explore, a Campground detail page, or a Recreation Area detail page with valid coordinates, **Then** the map renders using OpenFreeMap's default outdoor-legible vector style (`liberty`) with zero requests to OpenStreetMap's public raster tile server.
2. **Given** the default OpenFreeMap vector style is active, **When** the visitor pans and zooms across regional and campground-level zoom levels, **Then** map labels, roads, terrain, and park boundaries stay sharp and readable without raster pixelation or missing-tile errors.
3. **Given** the default OpenFreeMap vector style is active, **When** the map requests style documents, tiles, fonts, or icons, **Then** those requests remain isolated from application authentication cookies, authorization headers, and CSRF tokens, use an origin-only referrer policy, and respect standard browser HTTP caching.
4. **Given** a self-hosting operator deploys a prebuilt release artifact or container image without modifying basemap settings, **When** visitors browse maps, **Then** production-safe OpenFreeMap tiles work immediately with zero external accounts, API keys, proxy services, or additional infrastructure.

---

### User Story 2 - Custom Vector Style and Backwards-Compatible Raster Tile Overrides (Priority: P1)

As a self-hosting or enterprise operator with specific styling, privacy, SLA, or air-gapped requirements, I want to configure either a custom vector style address (such as another OpenFreeMap style or a self-hosted style) or retain an existing custom raster tile server with explicit attribution and zoom limits, so that I can tailor basemap hosting without breaking existing deployments.

**Why this priority**: Operators who have already configured custom raster tile servers (such as MapTiler, Stadia Maps, or a self-hosted tile server) must continue working seamlessly without migration breakage, while operators adopting vector tiles need a clean single setting to select an alternate hosted or self-hosted style.

**Independent Test**: Build the frontend under four distinct configuration profiles—(1) default with no overrides, (2) custom vector style URL, (3) custom raster tile URL with attribution and native zoom, and (4) both custom vector style URL and custom raster tile URL set together—plus invalid configuration inputs. Verify precedence, URL validation, attribution behavior, and local error recovery while keeping list search usable.

**Acceptance Scenarios**:

1. **Given** an operator sets a custom vector style address (an HTTPS URL or same-origin root-relative path) and leaves the custom raster tile setting unset, **When** the application is built and opened, **Then** all maps load that custom vector style and render the attribution declared by that style.
2. **Given** an operator sets a custom raster tile URL along with custom attribution text, a valid HTTPS attribution URL, and an optional native zoom limit (0–19), **When** the application is built and opened, **Then** all maps use that raster tile source, cap native tile requests at the configured zoom limit, and display the configured linked attribution.
3. **Given** an operator sets both a custom raster tile URL and a custom vector style URL, **When** the configuration is resolved, **Then** the explicit custom raster tile source takes precedence cleanly so existing raster deployments and test overrides are never silently overridden by a vector style default or setting.
4. **Given** an operator configures an unsafe or malformed style URL (such as plain HTTP, protocol-relative `//...`, `javascript:`, or embedded `user:pass@` credentials) or an invalid custom raster configuration (missing attribution, non-HTTPS attribution link, missing `{z}/{x}/{y}` tokens, or native zoom outside 0–19), **When** a visitor opens a map page, **Then** the map displays a clear local configuration error without attempting unsafe requests, while search results and destination details remain fully usable.

---

### User Story 3 - Resilient Basemap Failure Recovery and Legible Attribution Across Viewports & Themes (Priority: P2)

As a camper viewing maps on desktop or mobile in light or dark mode—including during temporary tile-host outages—I want basemap attribution to stay readable without overflowing the screen and basemap errors to remain isolated with one-click recovery, so that search results and campground monitoring never break when the basemap has trouble.

**Why this priority**: Switching from an inline raster definition with a fixed internal source identifier to a remote vector style introduces two distinct failure modes (style-document load failure and source tile failure under provider-defined source identifiers) and longer multi-link attribution text that must fit cleanly on compact 375 px mobile screens in both light and dark themes.

**Independent Test**: Exercise Explore and detail maps at 375 px mobile and 1440 px desktop widths in both light and dark themes. Verify attribution legibility and zero horizontal overflow. Simulate (1) a style-document fetch failure and (2) an individual tile failure from a vector source, verifying distinct local error states, functioning retry actions, and uninterrupted list search.

**Acceptance Scenarios**:

1. **Given** the default OpenFreeMap style or a custom vector style is loaded, **When** a visitor views any map on desktop (1440 px) or mobile (375 px) in light or dark mode, **Then** the map displays the style's required attribution links clearly with readable contrast, no duplicate attribution entries, and zero page-level horizontal overflow.
2. **Given** a custom raster tile source is configured, **When** a visitor views any map on desktop or mobile in light or dark mode, **Then** the map displays the configured custom attribution link clearly without duplicating or appending default OpenStreetMap or OpenFreeMap credits.
3. **Given** a loaded basemap (vector or custom raster) encounters a transient tile-loading failure on any source identifier, **When** the failure occurs, **Then** the map shows a non-blocking basemap warning with a **Retry tiles** action, keeps markers and list results usable, and refreshes the failing basemap source(s) when retried.
4. **Given** a remote vector style document itself fails to load (for example due to network outage or upstream HTTP 503), **When** the failure occurs, **Then** the map shows a local error alert with a **Retry map** action that re-initializes the map when clicked, while search filters, pagination, destination details, and list results remain completely unaffected.

---

### User Story 4 - Deterministic, Offline-Safe Automated Map Verification (Priority: P2)

As a maintainer running automated tests, browser smoke checks, and visual regression snapshots locally or in CI, I want all automated map verification to run 100% offline with deterministic local fixtures and never send traffic to OpenFreeMap or OpenStreetMap, so that test suites stay fast, reliable, reproducible, and respectful of community tile infrastructure.

**Why this priority**: Automated CI runs and visual snapshot suites must never depend on third-party uptime or generate synthetic load against community-funded map servers, while still verifying the real default style-loading path, attribution layout, error recovery, and custom raster overrides.

**Independent Test**: Run the unit test suite, browser map verification suite, and visual snapshot checks in an environment where external map hosts are intercepted or unreachable. Confirm zero live requests to OpenFreeMap or OpenStreetMap, passing header-isolation and retry checks, and deterministic visual captures across desktop/mobile and light/dark themes.

**Acceptance Scenarios**:

1. **Given** the automated visual snapshot suite runs across Explore, Campground detail, and Recreation Area detail scenarios, **When** maps render in the headless browser, **Then** all default OpenFreeMap requests are intercepted locally with deterministic fixtures, zero external map network traffic occurs, and maps settle cleanly to their idle state before capture.
2. **Given** the automated browser map verification suite runs, **When** it tests default basemap loading, **Then** it intercepts OpenFreeMap style and tile requests locally, confirms zero requests to `tile.openstreetmap.org`, verifies absence of authentication/CSRF headers and presence of an origin-only referrer, verifies visible attribution links, and exercises both tile-failure retry and style-fetch retry recovery.
3. **Given** the automated browser map verification suite tests custom overrides, **When** it builds with custom raster tile settings under a URL subpath and separately tests invalid basemap configuration, **Then** custom raster attribution, native zoom caps, subpath asset loading, and local invalid-configuration recovery all pass deterministically.

---

### Edge Cases

- **Both custom raster URL and custom style URL set**: Explicit custom raster tile URL takes precedence cleanly over both the default OpenFreeMap style and any custom vector style URL.
- **Whitespace-only or empty configuration values**: Empty strings or whitespace-only values (such as unset container build arguments passed as `""`) are treated as unset and fall back cleanly to the OpenFreeMap default rather than failing validation.
- **Default native zoom present without custom raster URL**: Build pipelines that always pass a default native zoom value (such as `19`) with an empty custom raster URL must remain in default vector style mode and must not trigger raster validation errors.
- **Unsafe or credentialed URLs**: Plain `http://` URLs, protocol-relative `//example.com/...` URLs, `javascript:` or `data:` schemes, URLs containing `username:password@` credentials, and malformed URLs are rejected with an explicit local map configuration error before map initialization.
- **Same-origin root-relative style paths**: Root-relative paths starting with a single `/` (such as `/styles/liberty.json`) are accepted for self-hosted or reverse-proxied styles, including under subpath deployments when configured accordingly.
- **Non-default vector source identifiers on tile failure**: Vector styles define arbitrary source names (for example `openmaptiles` in OpenFreeMap rather than `basemap`). Tile error detection and **Retry tiles** must handle any source identifier present in the active style without misclassifying tile errors as fatal map initialization errors.
- **Remote style JSON unavailable on initial load**: Unlike inline raster styles, a remote vector style URL can fail before any source exists. This must clear the loading status, present a local recoverable **Retry map** alert, and leave search results and destination details usable.
- **Long multi-link attribution on 375 px mobile screens**: OpenFreeMap's default attribution contains multiple links (`OpenFreeMap`, `© OpenMapTiles`, `OpenStreetMap`). It must wrap cleanly inside the map corner without colliding with controls, losing contrast in light/dark mode, or causing document-level horizontal overflow.
- **Offline/CI test execution**: Neither unit tests, visual snapshots, nor browser verification may issue live network requests to `tiles.openfreemap.org` or `tile.openstreetmap.org`.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: All interactive maps (Explore, Campground detail, and Recreation Area detail) MUST default to OpenFreeMap's `liberty` vector style (`https://tiles.openfreemap.org/styles/liberty`) when no custom basemap source is configured, eliminating all default requests to OpenStreetMap's public raster tile server (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`). _(Story 1)_
- **FR-002**: The default basemap MUST work without requiring any API key, third-party account, tile proxy server, edge worker, or backend configuration. _(Story 1)_
- **FR-003**: Operators MUST be able to override the default vector basemap by specifying a custom public vector style URL at frontend build time. _(Story 2)_
- **FR-004**: Operators MUST retain full backwards compatibility for configuring a custom raster XYZ tile source along with required custom attribution text, HTTPS attribution URL, and integer native zoom limit (`0`–`19`). _(Story 2)_
- **FR-005**: Basemap source resolution MUST follow strict deterministic precedence: (1) non-empty custom raster tile URL selects raster mode; (2) otherwise, non-empty custom vector style URL selects that vector style; (3) otherwise, the OpenFreeMap `liberty` vector style default is selected. Empty or whitespace-only values MUST be treated as unset, and raster-only companion settings (such as a default native zoom value) MUST NOT trigger raster mode when no custom raster tile URL is provided. _(Story 2)_
- **FR-006**: Every configured vector style URL MUST be validated before map initialization: it MUST be either an `https://` URL or a same-origin root-relative path beginning with `/` (and not `//`), MUST parse as a valid URL, and MUST NOT contain embedded username or password credentials. Invalid style or raster configurations MUST fail safely with an explicit local map error alert while keeping the rest of the page (including Explore search results and destination details) fully usable. _(Story 2)_
- **FR-007**: In vector style mode, maps MUST render the attribution declared by the loaded style/sources automatically without injecting duplicate attribution text. In custom raster mode, maps MUST render only the validated operator-configured attribution link built safely without raw HTML interpolation of untrusted input. _(Stories 1, 2, 3)_
- **FR-008**: Attribution controls MUST remain legible with accessible contrast and cause zero document-level horizontal overflow across both 375 px mobile and 1440 px desktop viewports in light and dark appearance modes. _(Story 3)_
- **FR-009**: Map network requests for vector styles, tiles, sprites, and fonts MUST remain separate from the authenticated API client, MUST NOT send cross-origin credentials, authorization headers, or CSRF tokens, MUST use an origin-only referrer policy, and MUST preserve ordinary browser HTTP caching. _(Stories 1, 4)_
- **FR-010**: Transient source/tile failures from any basemap source identifier (whether vector sources such as `openmaptiles` or custom raster source `basemap`) MUST surface a non-blocking basemap warning with a **Retry tiles** action that refreshes the failed source(s) without unmounting the map or clearing search state. Style-document load failures without a source identifier MUST surface a local recoverable error alert with a **Retry map** action that re-initializes the map while preserving list search and destination content. _(Story 3)_
- **FR-011**: Frontend build, packaging, and local container build pipelines MUST forward the public vector style setting alongside existing public map settings and track it in build freshness manifests without exposing unrelated or private environment variables. _(Story 2)_
- **FR-012**: Automated unit tests, browser map verification, and visual regression snapshot suites MUST execute completely offline with deterministic local fixtures, MUST intercept default OpenFreeMap requests, MUST verify zero requests to `tile.openstreetmap.org`, and MUST cover default vector style loading, custom style overrides, custom raster overrides, invalid-configuration recovery, and tile/style failure retries. _(Story 4)_

### Key Entities

- **Basemap Configuration**: Resolved, immutable build-time description of how maps obtain cartography. Takes one of two mutually exclusive forms: **Vector Style Basemap** (a validated HTTPS or same-origin root-relative style document URL, defaulting to OpenFreeMap `liberty`) or **Custom Raster Basemap** (a validated XYZ tile template URL, required plain-text credit, validated HTTPS attribution link, and integer native zoom cap `0`–`19`).
- **Basemap Attribution**: Visible, linked data/service credit displayed in the map corner. Supplied automatically from the style document and its tile sources in vector mode, or constructed safely from explicit operator settings in custom raster mode.
- **Basemap Failure State**: Local map-scoped recovery state distinguishing (a) configuration validation failure, (b) style-load or renderer failure (recoverable via **Retry map**), and (c) source/tile failure across one or more source identifiers (non-blocking warning recoverable via **Retry tiles**).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Default builds make **0** requests to `tile.openstreetmap.org` across Explore, Campground detail, and Recreation Area detail pages, achieving full compliance with OpenStreetMap's Tile Usage Policy at **$0/month** infrastructure cost and **0** new deployed services.
- **SC-002**: 100% of interactive map surfaces render OpenFreeMap's default vector basemap with zero required credentials or configuration changes in local development, standalone installations, container deployments, and static builds.
- **SC-003**: 100% of existing custom raster tile override configurations continue to take precedence and pass validation without modification, and 100% of tested unsafe/invalid style or raster URLs are blocked locally with the search list remaining usable.
- **SC-004**: Maps on 375 px mobile and 1440 px desktop viewports in both light and dark themes display complete, legible attribution with **0 px** of unintended document-level horizontal overflow and **0** duplicate attribution entries.
- **SC-005**: Simulated tile failures on vector sources and simulated style-document outages both recover in **1 click** (**Retry tiles** / **Retry map**) while keeping search results and destination details continuously interactive.
- **SC-006**: 100% of automated unit tests, browser map verification checks, and visual snapshot scenarios pass offline with **0** live external requests to OpenFreeMap or OpenStreetMap.
- **SC-007**: Operator configuration, environment template, architecture, and checklist documentation reflect the OpenFreeMap default, precedence rules, privacy/no-SLA tradeoffs, and self-hosting options with **0** broken links or stale default references.

## Assumptions

- **Single cartographic style across light and dark UI modes**: Keeping OpenFreeMap's `liberty` style active in both light and dark UI modes preserves rich outdoor cartography (parks, forests, topography, waterways, and trails) that campers rely on when locating campgrounds, avoids runtime style-reload flicker or theme-toggle race conditions, and keeps configuration minimal. Existing high-contrast attribution pill, marker, and tooltip styling ensures legibility in dark mode. Operators who prefer a dark basemap can select `https://tiles.openfreemap.org/styles/dark` (or `positron`, `bright`, `fiord`) via the single vector style build setting.
- **Build-time configuration only (no runtime basemap endpoint)**: Public basemap configuration remains build-time only, matching the existing architecture. Because the built-in OpenFreeMap default is already production-ready, free, and OSM-policy-compliant, prebuilt container images and Python packages no longer require runtime overrides for production use. Introducing a runtime configuration endpoint or HTML template injection is explicitly out of scope to keep the design simple and zero-infra; operators requiring custom tiles or air-gapped styles rebuild from source with build-time overrides.
- **No SLA on OpenFreeMap public service**: OpenFreeMap's public endpoint (`tiles.openfreemap.org`) is community-operated and provided as-is without a contractual SLA. Documentation will clearly distinguish open-source software/data licensing from hosted tile availability and point operators with strict SLA or air-gapped requirements to custom hosted or self-hosted style/tile overrides.
- **Zero backend or database changes**: This feature touches only frontend basemap configuration/rendering, build/packaging build-arg forwarding, automated test fixtures, and documentation. No database migrations, API endpoints, or worker changes are required.
