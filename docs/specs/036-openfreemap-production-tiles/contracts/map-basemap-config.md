# Contract: Production Basemap Configuration & MapLibre Behavior

**Feature**: `036-openfreemap-production-tiles`  
**Date**: 2026-11-27  
**Related**: [spec.md](../spec.md) | [data-model.md](../data-model.md) | [plan.md](../plan.md)

This contract supersedes the **Public Build-Time Settings** and **Tile-Service Policy** sections of [010-open-source-explore-maps/contracts/map-ui-and-configuration.md](../../010-open-source-explore-maps/contracts/map-ui-and-configuration.md) while preserving all UI layout, marker, group, coordinate, and keyboard accessibility contracts unchanged.

---

## 1. Public Build-Time Environment Variables

All `VITE_MAP_*` variables are **public frontend build-time settings** embedded into the static JavaScript bundle during Vite compilation.

- **Never place secrets or private tokens in `VITE_MAP_*` variables.**
- Changes require rebuilding the frontend bundle (or rebuilding the Docker image/wheel from source). No runtime configuration endpoint or HTML template injection is introduced.
- A root backend `.env` file is not automatically read by Vite unless exported into the frontend build environment or forwarded by Docker Compose build arguments.

| Variable                    | Default                                        | Applicability                                                                                 | Validation Contract                                                                                                                                           |
| --------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VITE_MAP_STYLE_URL`        | `https://tiles.openfreemap.org/styles/liberty` | Vector style mode (active when `VITE_MAP_TILE_URL` is unset/empty)                            | HTTPS URL (`https://...`) or same-origin root-relative path (`/...`, not `//...`), no whitespace, valid URL, no embedded username/password                    |
| `VITE_MAP_TILE_URL`         | _(unset)_                                      | Selects custom raster XYZ mode when non-empty; **takes precedence over `VITE_MAP_STYLE_URL`** | HTTPS URL (`https://...`) or same-origin root-relative path (`/...`, not `//...`), MUST include `{z}`, `{x}`, `{y}`, valid URL, no embedded username/password |
| `VITE_MAP_ATTRIBUTION_TEXT` | _(unset)_                                      | Required when `VITE_MAP_TILE_URL` is set; ignored in vector style mode                        | Non-empty plain text after trim                                                                                                                               |
| `VITE_MAP_ATTRIBUTION_URL`  | _(unset)_                                      | Required when `VITE_MAP_TILE_URL` is set; ignored in vector style mode                        | Valid `https://` URL, no embedded username/password                                                                                                           |
| `VITE_MAP_MAX_NATIVE_ZOOM`  | `19`                                           | Used only when `VITE_MAP_TILE_URL` is set; ignored in vector style mode                       | Integer `0`–`19`; MapLibre may overzoom up to map zoom `19`                                                                                                   |

### Build & Packaging Propagation Contract

The following build entrypoints MUST forward `VITE_MAP_STYLE_URL` alongside the four raster variables:

1. `src/frontend/vite-env.d.ts` (`ImportMetaEnv` type definitions)
2. `src/hatchling/plugin.py` (`PUBLIC_SETTINGS` whitelist and `build/frontend-manifest.json` input digest)
3. `Dockerfile` (`ARG VITE_MAP_STYLE_URL` and `ENV VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL` in `application-build`)
4. `docker-compose.yaml` (`VITE_MAP_STYLE_URL: ${VITE_MAP_STYLE_URL:-}` under `x-camply.build.args`)

---

## 2. Precedence Matrix

| Scenario                                       | `VITE_MAP_STYLE_URL`                                                                           | `VITE_MAP_TILE_URL`                          | `VITE_MAP_ATTRIBUTION_*` | `VITE_MAP_MAX_NATIVE_ZOOM` | Resulting Behavior                                                                                      |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------- |
| Zero-config default (local, Pages, GHCR, PyPI) | unset / `""`                                                                                   | unset / `""`                                 | unset / `""`             | unset or `"19"`            | Vector style: `https://tiles.openfreemap.org/styles/liberty`                                            |
| Alternate OpenFreeMap or custom vector style   | `https://tiles.openfreemap.org/styles/bright` (or `/styles/custom.json`)                       | unset / `""`                                 | unset / ignored          | unset or `"19"` / ignored  | Vector style: configured `VITE_MAP_STYLE_URL`                                                           |
| Invalid custom vector style                    | `http://insecure.example/style.json` or `javascript:alert(1)` or `https://u:p@host/style.json` | unset / `""`                                 | unset                    | unset                      | Throws validation error → local `role="alert"` in map; list search stays usable                         |
| Custom raster XYZ override                     | unset / `""`                                                                                   | `https://tiles.example.test/{z}/{x}/{y}.png` | valid text + HTTPS URL   | `"16"` (or unset → `19`)   | Inline raster style with `tiles: [url]`, `maxzoom: 16`, safe DOM attribution link                       |
| Both style URL and raster URL set              | `https://tiles.openfreemap.org/styles/bright`                                                  | `/tiles/{z}/{x}/{y}.png`                     | valid text + HTTPS URL   | `"4"`                      | **Raster wins**: inline raster style `/tiles/{z}/{x}/{y}.png` with `maxzoom: 4`                         |
| Custom raster URL missing attribution          | unset or set                                                                                   | `/tiles/{z}/{x}/{y}.png`                     | missing text or URL      | unset or `"19"`            | Throws validation error (`Custom map source requires attribution text and URL.`) → local `role="alert"` |
| Custom raster URL with invalid zoom            | unset or set                                                                                   | `/tiles/{z}/{x}/{y}.png`                     | valid text + HTTPS URL   | `"25"`                     | Throws validation error (`Map native zoom must be an integer from 0 to 19.`) → local `role="alert"`     |

---

## 3. MapLibre Style Loading, Requests, Attribution & Error Contract

### Initialization

- **Vector style mode (`config.kind === "style"`)**: Pass `style: config.styleUrl` directly to `new LibreMap({ ... })`. Keep `minZoom: 0`, `maxZoom: 19`, `maxPitch: 0`, `dragRotate: false`, `renderWorldCopies: true`, `attributionControl: false`, `fadeDuration: 0`.
- **Custom raster mode (`config.kind === "raster"`)**: Build the inline `StyleSpecification` (`version: 8`) with `sources.basemap` (`type: "raster"`, `tiles: [config.url]`, `tileSize: 256`, `minzoom: 0`, `maxzoom: config.maxNativeZoom`, `attribution: credit.outerHTML`) and `layers: [{ id: "basemap", type: "raster", source: "basemap", paint: { "raster-fade-duration": 0 } }]`, where `credit` is a DOM `<a>` element created via `document.createElement("a")` with `textContent = config.text`, `href = config.link`, `target = "_blank"`, `rel = "noopener noreferrer"`.

### Request Isolation (`transformRequest`)

Every request initiated by MapLibre (style JSON, TileJSON, vector/raster tiles, sprites, and glyph PBFs) MUST pass through:

```ts
transformRequest: (url) => ({
  url,
  credentials: "same-origin",
  referrerPolicy: "strict-origin",
});
```

- Cross-origin requests to OpenFreeMap or third-party hosts MUST NOT include cookies, `Authorization`, or `X-CSRF-Token`.
- No `cache` override (no cache-busting query params or `cache: "no-store"`), preserving ordinary browser HTTP caching.

### Attribution Rendering

- Always attach `new AttributionControl({ compact: false })` at `"bottom-right"`.
- In vector style mode, MapLibre automatically renders source attribution from the loaded style/TileJSON (for OpenFreeMap: `OpenFreeMap © OpenMapTiles Data from OpenStreetMap`). No duplicate `customAttribution` is injected.
- In custom raster mode, MapLibre renders `sources.basemap.attribution` (the single validated operator link).
- Attribution styling in `.camply-map .maplibregl-ctrl-attrib` MUST maintain accessible contrast in both light and dark modes and MUST NOT cause document-level horizontal overflow at 375 px or 1440 px viewports.

### Failure & Recovery Semantics

- **Source / tile error**: When MapLibre emits `"error"` with a non-empty string `event.sourceId` (e.g., `"openmaptiles"` in OpenFreeMap or `"basemap"` in custom raster mode), add `event.sourceId` to the tracked failed-source set and display the non-blocking `role="status"` warning with **Retry tiles**. Clicking **Retry tiles** hides the warning, calls `map?.refreshTiles(id)` for every tracked failed `sourceId`, and clears the tracked set.
- **Style-load / fatal error**: When `basemapConfig()` throws, `new LibreMap(...)` throws, `"webglcontextlost"` fires, or MapLibre emits `"error"` without a non-empty `sourceId` (such as a failed remote style JSON fetch), display the local `role="alert"` error message with **Retry map**. Clicking **Retry map** remounts the map instance while preserving saved camera state and without affecting list search or destination details.

---

## 4. Offline Automated Verification Contract

Browser verification (`src/frontend/tooling/verify-maps.ts`) and visual regression snapshots (`src/frontend/tooling/run-snapshots.ts`) MUST adhere to:

1. **Zero external map traffic**: Intercept `https://tiles.openfreemap.org/**` before navigation:
   - `https://tiles.openfreemap.org/styles/**` → HTTP 200 `application/json` with `Access-Control-Allow-Origin: *` returning a deterministic minimal MapLibre v8 Style JSON with source `"openmaptiles"`, `tiles: ["https://tiles.openfreemap.org/fixture-tiles/{z}/{x}/{y}.png"]`, `tileSize: 256`, `maxzoom: 19`, and OpenFreeMap's attribution links (`OpenFreeMap`, `© OpenMapTiles`, `OpenStreetMap`).
   - `https://tiles.openfreemap.org/fixture-tiles/**` → HTTP 200 `image/png` with `Access-Control-Allow-Origin: *` returning the deterministic 256×256 `rgb(225, 235, 219)` PNG fixture.
2. **Zero legacy OSM requests**: Assert that zero requests are made to `https://tile.openstreetmap.org/**`.
3. **Header & referrer verification**: Assert that intercepted OpenFreeMap style and tile requests carry no `authorization` or `x-csrf-token` headers and send an origin-only `referer` (`pathname === "/"`).
4. **Dual failure recovery**: `verify-maps.ts` MUST verify both (a) tile failure on `fixture-tiles/**` (`sourceId: "openmaptiles"`) recovering via **Retry tiles**, and (b) style-document failure on `styles/**` recovering via **Retry map**.
5. **Custom override & invalid-config verification**: `verify-maps.ts` MUST continue verifying custom `VITE_MAP_TILE_URL` static subpath builds and invalid configuration recovery (covering both invalid `VITE_MAP_STYLE_URL` and invalid `VITE_MAP_MAX_NATIVE_ZOOM`).

---

## 5. Security, Privacy & CSP Guidance

- **OpenFreeMap Terms & Privacy**: OpenFreeMap (`tiles.openfreemap.org`) is free and open-source (MIT software, ODbL OpenStreetMap data), permits commercial/public web use, requires attribution, and is operated as-is without a contractual SLA. External tile hosts observe client IP addresses and requested tile/style coordinates; self-hosting a style/tile server avoids that external dependency.
- **Content Security Policy (CSP)**: Deployments enforcing strict CSP must permit:
  - `worker-src 'self' blob:` (for MapLibre's bundled same-origin Vite worker)
  - `connect-src` and `img-src` for the configured style/tile origin (default `https://tiles.openfreemap.org`) to load style JSON, TileJSON, vector tiles, sprites, and glyphs.
