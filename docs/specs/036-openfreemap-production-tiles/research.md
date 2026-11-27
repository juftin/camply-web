# Research & Design Decisions: OpenFreeMap Production Map Tiles

**Feature**: `036-openfreemap-production-tiles`  
**Date**: 2026-11-27  
**Spec**: [spec.md](spec.md)

## 1. Codebase Audit Findings

An audit of the current mapping implementation, build pipelines, tests, and documentation identified the exact touchpoints affected by replacing OpenStreetMap's public raster tiles (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) with OpenFreeMap vector tiles:

| Area                     | Existing File                                                                                                                                                                                    | Current Behavior & Findings                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Basemap config           | `src/frontend/lib/maps.ts`                                                                                                                                                                       | `basemapConfig()` (lines 113–157) always returns raster `{ url, text, link, maxNativeZoom }`, defaulting `url` to `https://tile.openstreetmap.org/{z}/{x}/{y}.png`.                                                                                                                                                                                                                                                 |
| Env types                | `src/frontend/vite-env.d.ts`                                                                                                                                                                     | Declares `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_TEXT`, `VITE_MAP_ATTRIBUTION_URL`, `VITE_MAP_MAX_NATIVE_ZOOM`; does not declare `VITE_MAP_STYLE_URL`.                                                                                                                                                                                                                                                           |
| Map component            | `src/frontend/components/MapComponent.tsx`                                                                                                                                                       | Always builds an inline raster `StyleSpecification` with source id `"basemap"` (lines 121–159). Error handler checks `event.sourceId === "basemap"` (line 197) and retry calls `map?.refreshTiles("basemap")` (line 437). Uses `maplibre-gl` `6.19.0` with `AttributionControl({ compact: false })`, `NavigationControl`, and `transformRequest` (`credentials: "same-origin"`, `referrerPolicy: "strict-origin"`). |
| Map CSS                  | `src/frontend/index.css`                                                                                                                                                                         | Styles `.camply-map .maplibregl-ctrl-attrib` (`background: #fffe; color: #111827;`) and links (`color: #166534;`) for contrast in light and dark modes (lines 86–92).                                                                                                                                                                                                                                               |
| Unit tests               | `src/frontend/lib/maps.test.ts`                                                                                                                                                                  | Asserts default URL is `https://tile.openstreetmap.org/{z}/{x}/{y}.png` and tests raster validation (lines 59–78).                                                                                                                                                                                                                                                                                                  |
| Component tests          | `src/frontend/components/MapComponent.test.tsx`                                                                                                                                                  | Asserts default inline raster style with OSM tiles (lines 222–268) and tests `sourceId: "basemap"` retry (lines 408–428).                                                                                                                                                                                                                                                                                           |
| Visual snapshots         | `src/frontend/tooling/run-snapshots.ts`                                                                                                                                                          | Intercepts `https://tile.openstreetmap.org/**` with a deterministic 256×256 `rgb(225, 235, 219)` PNG (lines 2421–2434). Covers 18 `map-*` baselines in `tests/frontend/snapshots/baselines/`.                                                                                                                                                                                                                       |
| Browser map verification | `src/frontend/tooling/verify-maps.ts`                                                                                                                                                            | Intercepts `https://tile.openstreetmap.org/**` across default, tile-failure, touch, and WebGL-recovery pages (lines 81, 415, 461, 502); also builds a static subpath bundle with custom `VITE_MAP_TILE_URL` (lines 558–654) and tests invalid `VITE_MAP_MAX_NATIVE_ZOOM="25"` (lines 661–685).                                                                                                                      |
| Snapshot navigation      | `src/frontend/tooling/snapshot-navigation.ts`                                                                                                                                                    | Waits for `.camply-map[data-map-idle="true"]` (behavior is agnostic to raster vs vector tiles; only comment on line 3 says "raster tiles").                                                                                                                                                                                                                                                                         |
| Python build hook        | `src/hatchling/plugin.py`                                                                                                                                                                        | Whitelists `PUBLIC_SETTINGS` (lines 21–27) for Vite build forwarding and `build/frontend-manifest.json` freshness digests; needs `VITE_MAP_STYLE_URL`.                                                                                                                                                                                                                                                              |
| Build hook tests         | `tests/test_frontend_build.py`                                                                                                                                                                   | `test_manifest_records_only_supported_public_settings` verifies whitelisted public `VITE_MAP_*` settings.                                                                                                                                                                                                                                                                                                           |
| Docker & Compose         | `Dockerfile`, `docker-compose.yaml`                                                                                                                                                              | Forward `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_TEXT`, `VITE_MAP_ATTRIBUTION_URL`, `VITE_MAP_MAX_NATIVE_ZOOM=19`. Notably, `VITE_MAP_MAX_NATIVE_ZOOM` is **always** `"19"` in Docker builds even when `VITE_MAP_TILE_URL` is empty.                                                                                                                                                                              |
| Docs                     | `docs/operations/CONFIGURATION.md`, `docs/examples/.env.example`, `docs/architecture/DESIGN_FRONTEND.md`, `docs/specs/010-open-source-explore-maps/TODO.md`, `docs/CHECKLIST.md`, `docs/PLAN.md` | Document `tile.openstreetmap.org` as default and track `T3.3.6` as open.                                                                                                                                                                                                                                                                                                                                            |

---

## 2. Production Tile Strategy Comparison

### Decision

Use **OpenFreeMap** (`https://tiles.openfreemap.org/styles/liberty`) as the default MapLibre GL JS vector style.

### Rationale

- **$0/month and zero extra infrastructure**: No Cloudflare Worker, no tile cache server, no R2/S3 bucket, no API key, and no account registration.
- **OSM Tile Usage Policy compliant**: OpenFreeMap hosts its own CDN-backed vector tiles generated from OpenStreetMap + OpenMapTiles data, permits commercial and public web usage without hard request limits, and enables CORS by default for browser embeds.
- **Better outdoor cartography & rendering**: MapLibre GL JS already ships in the frontend bundle (`maplibre-gl` `6.19.0`). Vector tiles render crisp text, roads, trails, parks, waterways, and elevation/landcover detail at any device pixel ratio and zoom cleanly up to zoom 19 without raster blur.
- **Automatic attribution**: OpenFreeMap's style JSON/TileJSON embeds the required OpenFreeMap, OpenMapTiles, and OpenStreetMap attribution links, which MapLibre's `AttributionControl({ compact: false })` displays automatically.
- **Works everywhere by default**: Prebuilt GHCR Docker images, PyPI wheels (`camply serve`), Cloudflare Pages builds, and local Vite dev servers all inherit production-safe tiles with zero operator setup.

### Alternatives Considered

| Option                                                | Monthly Cost            | Extra Infra                           | API Key / Account        | OSM Policy Compliant                                          | Notes / Why Not Chosen as Default                                                                                                                                                              |
| ----------------------------------------------------- | ----------------------- | ------------------------------------- | ------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **OpenFreeMap (`liberty` vector style)** _(Selected)_ | **$0**                  | **None**                              | **No**                   | **Yes**                                                       | Zero setup, crisp outdoor vector cartography, CORS enabled, automatic attribution. No contractual SLA (documented; operators can override).                                                    |
| **MapTiler / Stadia Maps**                            | $0 free tier, then paid | None                                  | Yes (per-deployment key) | Yes                                                           | Requires signup and an API key; unsuitable as an out-of-the-box open-source default; free tier caps requests (~100k/mo). Remains supported via `VITE_MAP_STYLE_URL` or `VITE_MAP_TILE_URL`.    |
| **Cloudflare Worker OSM Reverse Proxy**               | $0–$5+                  | Cloudflare Worker + caching rules     | Yes (Cloudflare account) | Conditional (requires custom User-Agent & caching discipline) | Only works on Cloudflare deployments—leaves GHCR Docker, Helm, and standalone Python installs still hitting `tile.openstreetmap.org`. Adds operational surface area.                           |
| **Self-Hosted PMTiles / Martin**                      | Storage + egress        | S3/R2 bucket or tile server container | Yes (hosting infra)      | Yes                                                           | Heavy operational burden (multi-GB planet/region extracts and periodic refreshes) for an open-source default. Remains supported for operators via `VITE_MAP_STYLE_URL` or `VITE_MAP_TILE_URL`. |

---

## 3. Configuration Precedence & Backwards Compatibility

### Decision

Introduce `VITE_MAP_STYLE_URL` (defaulting to `https://tiles.openfreemap.org/styles/liberty`) and resolve basemap mode with explicit precedence:

1. If trimmed `VITE_MAP_TILE_URL` is non-empty → **Custom Raster mode** (`kind: "raster"`), ignoring `VITE_MAP_STYLE_URL`. Requires `VITE_MAP_ATTRIBUTION_TEXT`, valid HTTPS `VITE_MAP_ATTRIBUTION_URL`, and integer `VITE_MAP_MAX_NATIVE_ZOOM` (`0`–`19`, default `19`).
2. Else if trimmed `VITE_MAP_STYLE_URL` is non-empty → **Custom Vector Style mode** (`kind: "style"`), validating `VITE_MAP_STYLE_URL`.
3. Else → **Default OpenFreeMap Vector Style mode** (`kind: "style"`, `styleUrl: "https://tiles.openfreemap.org/styles/liberty"`).

### Rationale

- **100% backwards compatibility**: Existing operators who already set `VITE_MAP_TILE_URL` + `VITE_MAP_ATTRIBUTION_*` continue working unchanged even if a build template passes a default or empty `VITE_MAP_STYLE_URL`.
- **Docker/Compose safety**: Both `Dockerfile` (`ARG VITE_MAP_MAX_NATIVE_ZOOM=19`) and `docker-compose.yaml` (`VITE_MAP_MAX_NATIVE_ZOOM: ${VITE_MAP_MAX_NATIVE_ZOOM:-19}`) always inject `VITE_MAP_MAX_NATIVE_ZOOM="19"` even when `VITE_MAP_TILE_URL` is empty (`""`). Ignoring raster-only companion variables whenever `VITE_MAP_TILE_URL` is empty prevents false validation failures in default container builds.
- **Clean discriminated return type**: Returning `BasemapConfig` as `{ kind: "style"; styleUrl: string } | { kind: "raster"; url: string; text: string; link: string; maxNativeZoom: number }` gives TypeScript strict exhaustive checking in `MapComponent.tsx`.

### Alternatives Considered

- **Style URL takes precedence over tile URL**: Rejected because any build pipeline or `.env` setting a default `VITE_MAP_STYLE_URL` would silently shadow an operator's existing `VITE_MAP_TILE_URL` raster override.
- **Error if both `VITE_MAP_STYLE_URL` and `VITE_MAP_TILE_URL` are set**: Rejected because Docker Compose or CI templates may keep one empty/defaulted while overriding the other; explicit documented precedence is simpler and less fragile.

---

## 4. Dark Mode Evaluation

### Decision

Keep a **single basemap style** (`https://tiles.openfreemap.org/styles/liberty` by default) across both light and dark UI modes. Do **not** add automatic theme-based style switching or a second `VITE_MAP_DARK_STYLE_URL` variable.

### Rationale

1. **Outdoor cartographic legibility**: `liberty` renders national parks, forests, green landcover, water bodies, and rural roads clearly for campground discovery. OpenFreeMap's `dark` style (a Carto Dark Matter fork) is a low-contrast gray urban dashboard palette that strips outdoor terrain cues.
2. **Lifecycle & test stability**: `MapComponent.tsx` intentionally owns one `LibreMap` instance per mount without calling `map.setStyle()`. Dynamic theme switching would require subscribing to `ThemeProvider` (breaking direct DOM `.dark` toggles in `verify-maps.ts` lines 330–333 and requiring `ThemeProvider` wrappers in unit tests) and managing `setStyle()` reload flicker, `idle` resets, and extra tile/glyph network fetches on every theme click.
3. **Existing dark-mode UI polish**: Markers already have crisp white outlines + shadows (`.camply-map-pin`), tooltips use theme tokens (`hsl(var(--card))`), and `.camply-map .maplibregl-ctrl-attrib` uses an opaque high-contrast badge (`#fffe` background, `#111827` text, `#166534` links) that reads cleanly in both light and dark modes.
4. **Opt-in flexibility preserved**: Operators who specifically want a dark basemap can set `VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/dark` (or `positron`, `bright`, `fiord`) with the single style variable.

### Alternatives Considered

- **Auto-switch between `liberty` (light) and `dark` (dark)**: Rejected due to poor outdoor cartography in `dark`, extra env var / magic heuristic complexity, `setStyle()` lifecycle/flicker risks, and YAGNI.

---

## 5. Build-Time `VITE_MAP_*` vs Runtime Overrides for Prebuilt GHCR Images

### Decision

Keep all `VITE_MAP_*` configuration strictly **build-time** (Vite static replacement, forwarded via `Dockerfile`, `docker-compose.yaml`, `src/hatchling/plugin.py`, and Cloudflare Pages). Explicitly scope out runtime basemap configuration endpoints or HTML injection.

### Rationale

- Previously, prebuilt GHCR images and PyPI wheels baked in `tile.openstreetmap.org`, which was unsuitable for production traffic. That created pressure to inject tile URLs at runtime.
- With OpenFreeMap (`https://tiles.openfreemap.org/styles/liberty`) baked in as the default, prebuilt GHCR images (`deploy/compose/*.yaml`, Helm chart) and PyPI wheels (`camply serve`) are **already production-ready at $0/month** with zero overrides.
- Adding a runtime `/api/map-config` endpoint or Nginx/FastAPI `index.html` script injection would introduce backend code, an extra network round-trip before map initialization (or HTML template mutation that breaks static asset hashing/CSP), and a new configuration/validation surface across standalone, Nginx, Cloudflare Pages, and Helm—violating Simplicity First / YAGNI and the existing contract in `docs/specs/010-open-source-explore-maps/contracts/map-ui-and-configuration.md`.
- Operators with specialized needs (custom commercial styles, self-hosted PMTiles/Martin, or air-gapped networks) can build the container or frontend with `VITE_MAP_STYLE_URL` or `VITE_MAP_TILE_URL` build arguments.

### Alternatives Considered

- **Runtime `GET /api/map-config` endpoint**: Rejected as unnecessary latency, backend coupling, and scope creep now that the default is production-safe.
- **Nginx `envsubst` / `window.__CAMPLY_CONFIG__` injection**: Rejected because `Dockerfile` explicitly forbids `envsubst` (`tests/release.test.mjs` line 492 asserts `assert.doesNotMatch(dockerfile, /envsubst/)`), and standalone Python + Cloudflare Pages serve static bundles directly.

---

## 6. MapLibre Error Handling & Retry Generalization

### Decision

Update `MapComponent.tsx` error handling and retry logic to distinguish:

1. **Source / tile errors** (`"sourceId" in event && typeof event.sourceId === "string" && event.sourceId.length > 0`): Record `event.sourceId` in a component-scoped `Set<string>` ref (`failedSources`) and set `tileError = true` (non-blocking warning banner). Clicking **Retry tiles** clears `tileError`, iterates over recorded source IDs, calls `map?.refreshTiles(sourceId)` for each, and clears the set.
2. **Style-document / renderer errors** (no `sourceId` on `event`): Set `error` (`role="alert"` banner with **Retry map** button, which increments `attempt` to cleanly rebuild the `LibreMap` instance and re-fetch the style URL).

### Rationale

- Currently, `MapComponent.tsx` hardcodes `event.sourceId === "basemap"` (line 197) and `map?.refreshTiles("basemap")` (line 437).
- OpenFreeMap's `liberty` style defines its vector source as `"openmaptiles"` (and other custom styles may define `"protomaps"`, `"maptiler_planet"`, etc.). Without generalizing `sourceId`, any transient vector tile 503 would fall into the fatal `else` branch (`setError(...)`), and clicking **Retry tiles** would target a non-existent `"basemap"` source.
- Generalizing to any non-empty `sourceId` preserves 100% compatibility with custom raster mode (`sourceId === "basemap"`) and existing unit test mocks (`MapComponent.test.tsx`), while handling OpenFreeMap and arbitrary custom vector styles cleanly.

### Alternatives Considered

- **Hardcode `event.sourceId === "basemap" || event.sourceId === "openmaptiles"`**: Rejected because custom `VITE_MAP_STYLE_URL` styles can name their sources anything.

---

## 7. Attribution Behavior & Mobile Viewport Legibility

### Decision

- Retain `attributionControl: false` in `new LibreMap(...)` and `instance.addControl(new AttributionControl({ compact: false }), "bottom-right")`.
- In vector style mode (`kind: "style"`), pass `style: config.styleUrl` directly and rely on MapLibre's built-in source/TileJSON attribution extraction—never inject extra `customAttribution` to avoid duplication.
- In custom raster mode (`kind: "raster"`), keep the existing safe DOM anchor (`document.createElement("a")` with `textContent`, validated `https://` `href`, `target="_blank"`, `rel="noopener noreferrer"`) assigned to `sources.basemap.attribution`.
- Verify `.camply-map .maplibregl-ctrl-attrib` wrapping, contrast, and zero document-level horizontal overflow at 375 px mobile and 1440 px desktop (light and dark themes) during browser verification (`verify-maps.ts` and `run-snapshots.ts`). If multi-link OpenFreeMap attribution needs tighter spacing or explicit `max-width` on 375 px screens, apply a minimal CSS rule in `src/frontend/index.css`.

### Rationale

- OpenFreeMap's TileJSON specifies `<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank">&copy; OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>`. MapLibre's `AttributionControl({ compact: false })` renders this automatically, keeping attribution always visible (never collapsed behind an icon) and preventing duplicate OSM links.

---

## 8. Offline-Safe Deterministic Playwright Mocking Strategy

### Decision

In both `src/frontend/tooling/run-snapshots.ts` and `src/frontend/tooling/verify-maps.ts`, intercept `https://tiles.openfreemap.org/**` locally instead of `https://tile.openstreetmap.org/**`:

- Requests matching `https://tiles.openfreemap.org/styles/**` return HTTP 200 `application/json` (with `Access-Control-Allow-Origin: *`) containing a minimal deterministic MapLibre v8 Style JSON with source `"openmaptiles"`, `tiles: ["https://tiles.openfreemap.org/fixture-tiles/{z}/{x}/{y}.png"]`, `tileSize: 256`, `maxzoom: 19`, and OpenFreeMap's real attribution HTML (`OpenFreeMap`, `© OpenMapTiles`, `OpenStreetMap`).
- Requests matching `https://tiles.openfreemap.org/fixture-tiles/**` return HTTP 200 `image/png` (with `Access-Control-Allow-Origin: *`) containing the existing deterministic 256×256 `rgb(225, 235, 219)` PNG.
- Add a guard route/assertion in `verify-maps.ts` (and `run-snapshots.ts`) confirming zero requests are ever issued to `https://tile.openstreetmap.org/**`.

### Rationale

- **Exercises the real production code path**: Both `run-snapshots.ts` and `verify-maps.ts` run the app with **no** `VITE_MAP_*` override, proving that `basemapConfig()` defaults to `https://tiles.openfreemap.org/styles/liberty`, passes the URL string to MapLibre GL JS, fetches the remote style JSON with `transformRequest` headers (`strict-origin`, no `Authorization`, no `X-CSRF-Token`), loads tiles under non-`"basemap"` source ID `"openmaptiles"`, renders OpenFreeMap's real multi-link attribution, and transitions `data-map-idle` to `"true"`.
- **100% offline & deterministic**: Zero external network fetches, zero remote glyph/sprite downloads, zero binary `.pbf` protobuf fixture complexity, and identical deterministic sage-green canvas fill across platforms.
- **Full failure-path coverage**: `verify-maps.ts` can independently abort `https://tiles.openfreemap.org/fixture-tiles/**` (testing `tileError` + **Retry tiles** for `"openmaptiles"`) AND abort `https://tiles.openfreemap.org/styles/**` (testing style-fetch failure + **Retry map**).
- **Visual baseline impact**: Because the bottom-right attribution bar changes from `© OpenStreetMap contributors` to `OpenFreeMap © OpenMapTiles Data from OpenStreetMap`, the affected `map-*` visual baselines in `tests/frontend/snapshots/baselines/` will be intentionally refreshed (visually confirming the new attribution pill at 375 px and 1440 px in both themes).

### Alternatives Considered

- **Force `VITE_MAP_TILE_URL` override in `run-snapshots.ts` Vite env**: Rejected because snapshot tests would skip the default vector style path and never visually verify OpenFreeMap's longer attribution bar on 375 px mobile.
- **Serve real binary `.pbf` vector tiles + glyph PBFs in fixtures**: Rejected as brittle, bloated, and unnecessary—MapLibre GL JS's style loader, `transformRequest`, source-ID error routing, attribution rendering, WebGL canvas, and `idle` events are exercised identically by a remote Style JSON referencing a local synthetic raster source.
