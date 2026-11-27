# Data Model: OpenFreeMap Production Map Tiles

**Feature**: `036-openfreemap-production-tiles`  
**Date**: 2026-11-27  
**Spec**: [spec.md](spec.md)

## Persistence Scope

This feature introduces **no database tables, columns, Alembic migrations, or backend API schema changes**. All entities live in frontend build-time configuration resolution (`src/frontend/lib/maps.ts`) and client-side map component state (`src/frontend/components/MapComponent.tsx`).

---

## 1. Constants & Input Model

### Default Constant

```ts
export const DEFAULT_MAP_STYLE_URL =
  "https://tiles.openfreemap.org/styles/liberty";
```

### Build-Time Environment Input (`BasemapEnvInput`)

Subset of `ImportMetaEnv` (`Record<string, string | undefined>`):

| Field                       | Type                  | Default When Unset/Empty              | Applicable Mode(s)                                          |
| --------------------------- | --------------------- | ------------------------------------- | ----------------------------------------------------------- |
| `VITE_MAP_STYLE_URL`        | `string \| undefined` | `DEFAULT_MAP_STYLE_URL`               | Vector style mode (when `VITE_MAP_TILE_URL` is unset/empty) |
| `VITE_MAP_TILE_URL`         | `string \| undefined` | `undefined` (unset)                   | Selects custom raster mode when trimmed value is non-empty  |
| `VITE_MAP_ATTRIBUTION_TEXT` | `string \| undefined` | `undefined` (required in raster mode) | Custom raster mode only                                     |
| `VITE_MAP_ATTRIBUTION_URL`  | `string \| undefined` | `undefined` (required in raster mode) | Custom raster mode only                                     |
| `VITE_MAP_MAX_NATIVE_ZOOM`  | `string \| undefined` | `"19"`                                | Custom raster mode only                                     |

---

## 2. Resolved Configuration Model (`BasemapConfig`)

`basemapConfig(env)` returns a discriminated union so callers handle vector styles and custom raster templates exhaustively:

```ts
export interface VectorStyleBasemapConfig {
  kind: "style";
  styleUrl: string;
}

export interface RasterTileBasemapConfig {
  kind: "raster";
  url: string;
  text: string;
  link: string;
  maxNativeZoom: number;
}

export type BasemapConfig = VectorStyleBasemapConfig | RasterTileBasemapConfig;
```

---

## 3. Precedence & Resolution Flow

```mermaid
flowchart TD
    Start["Read env: VITE_MAP_TILE_URL, VITE_MAP_STYLE_URL"] --> TrimTile["Trim VITE_MAP_TILE_URL"]
    TrimTile --> HasTile{"Non-empty VITE_MAP_TILE_URL?"}
    HasTile -- Yes --> RasterMode["Select Raster Mode (ignores VITE_MAP_STYLE_URL)"]
    RasterMode --> ValidateRaster["Validate tile URL, attribution text/URL, native zoom 0..19"]
    ValidateRaster -- Valid --> ReturnRaster["Return { kind: 'raster', url, text, link, maxNativeZoom }"]
    ValidateRaster -- Invalid --> ThrowError["Throw descriptive Error (caught by MapComponent local alert)"]
    HasTile -- No --> TrimStyle["Trim VITE_MAP_STYLE_URL"]
    TrimStyle --> PickStyle["styleUrl = non-empty trimmed value OR DEFAULT_MAP_STYLE_URL"]
    PickStyle --> ValidateStyle["Validate style URL (https:// or single-leading-/ path, valid URL, no credentials)"]
    ValidateStyle -- Valid --> ReturnStyle["Return { kind: 'style', styleUrl }"]
    ValidateStyle -- Invalid --> ThrowError
```

### Precedence Summary

| `VITE_MAP_TILE_URL` (trimmed) | `VITE_MAP_STYLE_URL` (trimmed) | Resolved Mode | Resolved Source                                                  |
| ----------------------------- | ------------------------------ | ------------- | ---------------------------------------------------------------- |
| empty / unset                 | empty / unset                  | `style`       | `https://tiles.openfreemap.org/styles/liberty`                   |
| empty / unset                 | non-empty                      | `style`       | Trimmed `VITE_MAP_STYLE_URL`                                     |
| non-empty                     | empty / unset                  | `raster`      | Trimmed `VITE_MAP_TILE_URL` + required raster attribution & zoom |
| non-empty                     | non-empty                      | `raster`      | Trimmed `VITE_MAP_TILE_URL` (raster override wins cleanly)       |

---

## 4. Field Validation Rules

Every validation failure throws a synchronous `Error` with a clear, user-readable message that `MapComponent` catches and displays in its local `role="alert"` container without instantiating MapLibre GL JS.

### Vector Style Mode (`kind: "style"`)

| Field      | Rule                                                                                                                              | Rejection Condition(s)                                                                                                      |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `styleUrl` | Trimmed string MUST start with `https://` OR start with `/` and NOT `//`                                                          | `http://...`, `//example.com/...`, `javascript:...`, `data:...`, relative paths without leading `/` (`styles/liberty.json`) |
| `styleUrl` | MUST NOT contain ASCII whitespace or control characters                                                                           | Embedded spaces, tabs, newlines                                                                                             |
| `styleUrl` | `new URL(styleUrl, "https://camply.invalid")` MUST succeed with `protocol === "https:"`, `username === ""`, and `password === ""` | Malformed URL syntax, embedded credentials (`https://user:pass@tiles.example/style.json`)                                   |

### Custom Raster Mode (`kind: "raster"`)

| Field                                        | Rule                                                                                                                                                                                                                                                                            | Rejection Condition(s)                                                                                   |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `text` (`VITE_MAP_ATTRIBUTION_TEXT`)         | Trimmed value MUST be non-empty                                                                                                                                                                                                                                                 | Unset, `""`, or whitespace-only                                                                          |
| `link` (`VITE_MAP_ATTRIBUTION_URL`)          | Trimmed value MUST be non-empty, MUST start with `https://`, MUST parse via `new URL(link)`, and MUST have `protocol === "https:"`, `username === ""`, `password === ""`                                                                                                        | Unset, `http://...`, `javascript:...`, malformed URL, embedded credentials                               |
| `url` (`VITE_MAP_TILE_URL`)                  | Trimmed value MUST start with `https://` OR start with `/` and NOT `//`; MUST contain all three tokens `{z}`, `{x}`, `{y}`; `new URL(url.replace(/\{[zxy]\}/g, "0"), "https://camply.invalid")` MUST succeed with `protocol === "https:"`, `username === ""`, `password === ""` | Non-HTTPS scheme, protocol-relative `//`, missing `{z}`/`{x}`/`{y}`, malformed URL, embedded credentials |
| `maxNativeZoom` (`VITE_MAP_MAX_NATIVE_ZOOM`) | Defaults to `"19"` when unset/empty; parsed number MUST satisfy `Number.isInteger(n) && n >= 0 && n <= 19`                                                                                                                                                                      | Non-numeric, float (`14.5`), negative (`-1`), greater than `19` (`20`, `25`), `NaN`, `Infinity`          |

---

## 5. Client-Side Map Recovery State (`MapComponent`)

`MapComponent` maintains four local UI states plus a tracked set of failing source identifiers:

| State Field           | Type          | Initial Value | Semantics                                                                                                                                                                                                              |
| --------------------- | ------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ready`               | `boolean`     | `false`       | Set `true` on MapLibre `"load"` event; hides `"Loading map…"` status                                                                                                                                                   |
| `idle`                | `boolean`     | `false`       | Set `false` on `"movestart"` / `"dataloading"`, `true` on `"idle"`; exposed as `data-map-idle`                                                                                                                         |
| `error`               | `string`      | `""`          | Non-empty on config validation error, WebGL/init throw, `"webglcontextlost"`, or MapLibre `"error"` without a non-empty `sourceId` (including remote style JSON fetch failure). Renders `role="alert"` + **Retry map** |
| `tileError`           | `boolean`     | `false`       | Set `true` on MapLibre `"error"` carrying a non-empty string `sourceId` (e.g., `"openmaptiles"` or `"basemap"`). Renders non-blocking `role="status"` + **Retry tiles**                                                |
| `failedSources` (ref) | `Set<string>` | empty `Set`   | Accumulates every non-empty `event.sourceId` observed in tile errors so **Retry tiles** calls `map?.refreshTiles(sourceId)` for each failed source and then clears the set                                             |

### State Transitions

| Trigger                                                                 | Transition                                                                                    | User-Facing Recovery                                                                                                            |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `basemapConfig()` throws                                                | `error = err.message`; `LibreMap` not created                                                 | `role="alert"` + **Retry map** (list remains usable)                                                                            |
| Remote style JSON fetch fails (`error` event without `sourceId`)        | `error = event.error?.message \|\| "Map could not load."`; loading indicator hidden           | `role="alert"` + **Retry map** (remounts `LibreMap` via `attempt + 1`)                                                          |
| Tile or TileJSON source error (`error` event with non-empty `sourceId`) | `failedSources.add(event.sourceId)`; `tileError = true`                                       | Non-blocking `role="status"` + **Retry tiles** (clears `tileError`, refreshes each recorded `sourceId`, clears `failedSources`) |
| `webglcontextlost`                                                      | `error = "The map graphics context was lost. Please retry the map."`                          | `role="alert"` + **Retry map** (remounts `LibreMap` preserving saved camera)                                                    |
| Map `"load"` succeeds                                                   | `ready = true`                                                                                | Map interactive; markers and attribution visible                                                                                |
| Click **Retry map**                                                     | `setMap(null); failedSources.clear(); setAttempt(n => n + 1)`                                 | Re-runs effect, resets `ready/idle/error/tileError`, re-initializes `LibreMap`                                                  |
| Click **Retry tiles**                                                   | `setTileError(false); for (id of failedSources) map?.refreshTiles(id); failedSources.clear()` | Re-requests tiles from the affected basemap source(s) using ordinary browser cache semantics                                    |
