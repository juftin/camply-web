# Implementation Plan: OpenFreeMap Production Map Tiles

**Branch**: `openfreemap-production-tiles` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from [spec.md](spec.md), backed by [research.md](research.md), [data-model.md](data-model.md), and [contracts/map-basemap-config.md](contracts/map-basemap-config.md).

## Summary

Replace OpenStreetMap's public raster tile server (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) as the default production basemap with **OpenFreeMap** (`https://tiles.openfreemap.org/styles/liberty`) via a new public build-time setting `VITE_MAP_STYLE_URL`. Keep full backwards compatibility for custom raster XYZ overrides (`VITE_MAP_TILE_URL` + `VITE_MAP_ATTRIBUTION_TEXT` + `VITE_MAP_ATTRIBUTION_URL` + `VITE_MAP_MAX_NATIVE_ZOOM`) with explicit raster precedence, generalize `MapComponent` tile error/retry handling to work with arbitrary vector style source IDs (such as `"openmaptiles"`), forward `VITE_MAP_STYLE_URL` across Hatchling packaging and Docker/Compose builds, update Playwright browser verification and visual snapshots to intercept OpenFreeMap offline deterministically, and update operator/architecture/checklist documentation.

## Technical Context

**Language/Version**: TypeScript 7 (`@typescript/native` 7.0.2) / React 18.3.1 / Vite 8.3.5; Python >=3.11 (3.14 default) for Hatchling build hook and packaging/compose/docs tests

**Primary Dependencies**: `maplibre-gl` `6.19.0` (already installed), Vitest `5.1.0`, `@playwright/test` `1.65.1`, `pngjs` `7.0.0`, Hatchling build plugin (`src/hatchling/plugin.py`)

**Storage**: N/A (no database models, migrations, or backend API changes)

**Testing**: Vitest (`task frontend:test`), Playwright browser map verification (`task maps:verify`), Playwright visual regression snapshots (`task snapshot:check`), pytest (`tests/test_frontend_build.py`, `tests/test_compose.py`, `tests/docs/test_docs.py`)

**Target Platform**: Modern web browsers supporting WebGL 2 (desktop 1440 px and mobile 375 px, light and dark modes), served via Vite/Cloudflare Pages, Nginx container (`camply serve frontend`), and standalone Python (`camply serve`)

**Project Type**: Full-stack monorepo web application (frontend-focused change with build/packaging/container plumbing)

**Performance Goals**: Zero additional network round-trips before map initialization (build-time config only); keep `verify-maps.ts` initial map render `< 3000 ms` and marker/group interactions `< 500 ms`; preserve native browser HTTP caching for style/tile/glyph/sprite assets

**Constraints**: $0/month production tile hosting; zero new infrastructure (no tile proxy, worker, or runtime config endpoint); strict OSM Tile Usage Policy compliance (0 default requests to `tile.openstreetmap.org`); 100% offline deterministic CI/Playwright tests; zero breaking changes for existing `VITE_MAP_TILE_URL` operators

**Scale/Scope**: Surgical change across ~6 frontend source/test files, 3 Playwright tooling files, 4 build/packaging/container files, affected `map-*` visual baselines, and 7 documentation/tracking files

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                                  | Pre-Design Check | Post-Design Check | Notes                                                                                                                                                                                                       |
| ------------------------------------------ | ---------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **I. Reliability & Precision**             | PASS             | PASS              | Eliminates OSM tile-server throttling/blocking risk in production; adds explicit style-fetch and multi-source tile retry recovery without impacting search or availability polling.                         |
| **II. Type Safety & Static Analysis**      | PASS             | PASS              | Introduces strict discriminated union `BasemapConfig` and `ImportMetaEnv.VITE_MAP_STYLE_URL`; validated by `task check` (`tsc`, `oxlint`, `oxfmt`, `mypy`, `ruff`, Import Linter).                          |
| **III. Modern Workflow & Automation**      | PASS             | PASS              | All verification runs through existing `task` targets (`task check`, `task test`, `task maps:verify`, `task snapshot:check`, `task docs:check`); Docker/Compose forward `VITE_MAP_STYLE_URL`.               |
| **IV. Monorepos & Separation of Concerns** | PASS             | PASS              | Changes stay cleanly in `src/frontend/`, `src/hatchling/plugin.py`, root container manifests, `tests/`, and `docs/`. No backend Python runtime dependencies added; editable Python installs remain JS-free. |
| **V. Automated Verification**              | PASS             | PASS              | Test-first updates to `maps.test.ts`, `MapComponent.test.tsx`, `tests/test_frontend_build.py`, `tests/test_compose.py`, `verify-maps.ts`, and `run-snapshots.ts`, all 100% offline and deterministic.       |

## Project Structure

### Documentation (this feature)

```text
docs/specs/20261127-143403-openfreemap-production-tiles/
├── spec.md                              # Feature specification (user stories, FR-*, SC-*)
├── plan.md                              # This file
├── research.md                          # Codebase audit & design tradeoffs
├── data-model.md                        # BasemapConfig union, precedence & validation rules
├── quickstart.md                        # Runnable local & CI validation scenarios
├── contracts/
│   └── map-basemap-config.md            # Env vars, precedence matrix, MapLibre & offline test contract
├── checklists/
│   └── requirements.md                  # Specification quality checklist
└── tasks.md                             # Dependency-ordered implementation tasks
```

### Source Code & Touchpoints (repository root)

All paths below exist in the repository today; no new source files are needed.

```text
Dockerfile                                         # Forward ARG/ENV VITE_MAP_STYLE_URL in application-build
docker-compose.yaml                                # Forward VITE_MAP_STYLE_URL in x-camply.build.args
src/
├── hatchling/
│   └── plugin.py                                  # Add VITE_MAP_STYLE_URL to PUBLIC_SETTINGS
└── frontend/
    ├── vite-env.d.ts                              # Add readonly VITE_MAP_STYLE_URL?: string
    ├── index.css                                  # Verify/tune mobile & dark attribution styling if needed
    ├── lib/
    │   ├── maps.ts                                # DEFAULT_MAP_STYLE_URL, BasemapConfig union, validation & precedence
    │   └── maps.test.ts                           # Unit tests for style default, overrides, precedence & rejection
    ├── components/
    │   ├── MapComponent.tsx                       # Vector style URL vs inline raster, multi-source error/retry
    │   └── MapComponent.test.tsx                  # Component tests for vector default, raster override, source/style retry
    └── tooling/
        ├── run-snapshots.ts                       # Intercept https://tiles.openfreemap.org/** offline
        ├── verify-maps.ts                         # Intercept OpenFreeMap offline, test style & source retry, guard 0 OSM calls
        └── snapshot-navigation.ts                 # Update comment for vector/raster basemap readiness
tests/
├── test_frontend_build.py                         # Verify VITE_MAP_STYLE_URL recorded in build/frontend-manifest.json
├── test_compose.py                                # Verify root docker-compose.yaml forwards VITE_MAP_STYLE_URL build arg
└── frontend/
    └── snapshots/
        └── baselines/                             # Refresh affected map-* baselines if attribution bar text changes
docs/
├── CHECKLIST.md                                   # Mark T3.3.6 complete with link to spec 036
├── PLAN.md                                        # Reference OpenFreeMap default in Map-Based Discovery
├── architecture/
│   └── DESIGN_FRONTEND.md                         # Document VITE_MAP_STYLE_URL + custom raster overrides
├── examples/
│   └── .env.example                               # Add commented VITE_MAP_STYLE_URL example
├── operations/
│   └── CONFIGURATION.md                           # Update Maps section with OpenFreeMap default, precedence & CSP
└── specs/
    ├── index.md                                   # Index feature 036
    └── 20261014-223122-open-source-explore-maps/
        └── TODO.md                                # Mark production tile hosting resolved by spec 036
```

**Structure Decision**: Reuse the existing single-module basemap helper (`src/frontend/lib/maps.ts`) and shared map component (`src/frontend/components/MapComponent.tsx`). No new modules, backend routes, or infrastructure files are needed.

## Phased Implementation Design

### Phase A: Build-Arg Plumbing & Type Definitions (Foundational)

1. Add `readonly VITE_MAP_STYLE_URL?: string;` to `ImportMetaEnv` in `src/frontend/vite-env.d.ts`.
2. Add `"VITE_MAP_STYLE_URL"` to `PUBLIC_SETTINGS` in `src/hatchling/plugin.py` so Python wheel/sdist builds forward it to Vite and include it in `build/frontend-manifest.json` input digests.
3. Add `ARG VITE_MAP_STYLE_URL` and `VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL` to the `application-build` stage of `Dockerfile`, and `VITE_MAP_STYLE_URL: ${VITE_MAP_STYLE_URL:-}` to `x-camply.build.args` in `docker-compose.yaml`.
4. Extend `tests/test_frontend_build.py` (and `tests/test_compose.py`) to verify `VITE_MAP_STYLE_URL` forwarding and manifest tracking.

### Phase B: Basemap Configuration Resolution & Validation

1. Update `src/frontend/lib/maps.ts`:
   - Export `DEFAULT_MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"`.
   - Export `VectorStyleBasemapConfig`, `RasterTileBasemapConfig`, and discriminated union `BasemapConfig`.
   - Implement strict resolution precedence in `basemapConfig(env)`:
     - Trimmed non-empty `VITE_MAP_TILE_URL` → raster mode (validates tile template URL, required attribution text, valid HTTPS attribution URL without credentials, and integer `VITE_MAP_MAX_NATIVE_ZOOM` in `0..19`).
     - Otherwise trimmed non-empty `VITE_MAP_STYLE_URL` or `DEFAULT_MAP_STYLE_URL` → style mode (validates `https://` or single-leading-`/` path, no whitespace, valid URL parse, `protocol === "https:"`, no embedded username/password).
2. Write comprehensive Vitest coverage in `src/frontend/lib/maps.test.ts` before modifying implementation (test-first per Constitution Principle V).

### Phase C: MapLibre Vector Style Rendering & Resilient Error Recovery

1. Update `src/frontend/components/MapComponent.tsx`:
   - Consume `BasemapConfig`: pass `style: config.styleUrl` in `"style"` mode, or construct the inline raster `StyleSpecification` with safe DOM attribution anchor in `"raster"` mode.
   - Track failing source identifiers in `failedSources = useRef<Set<string>>(new Set())`:
     - On `"error"` with non-empty string `event.sourceId`: add `event.sourceId` to `failedSources.current` and `setTileError(true)`.
     - On `"error"` without a non-empty `sourceId` (including remote style JSON fetch failures): `setError(event.error?.message || "Map could not load.")`.
     - On **Retry tiles**: clear `tileError`, call `map?.refreshTiles(id)` for every tracked source ID in `failedSources.current`, then clear `failedSources.current`.
     - On **Retry map** or cleanup: clear `failedSources.current` alongside remounting the map instance.
   - Preserve `transformRequest` (`credentials: "same-origin"`, `referrerPolicy: "strict-origin"`), `AttributionControl({ compact: false })`, `NavigationControl({ showCompass: false })`, `data-map-idle`, marker/tooltip behavior, and WebGL recovery unchanged.
2. Verify `.camply-map .maplibregl-ctrl-attrib` contrast and wrapping at 375 px mobile and 1440 px desktop in light/dark themes in `src/frontend/index.css` (adjust only if needed to prevent clipping or overflow).
3. Update `src/frontend/components/MapComponent.test.tsx` (test-first) to cover default OpenFreeMap style URL, custom style URL, custom raster fallback, non-`"basemap"` source retry (`"openmaptiles"`), style-fetch failure retry, and invalid style URL recovery.

### Phase D: Offline Deterministic Playwright Fixtures & Visual Baselines

1. Update `src/frontend/tooling/run-snapshots.ts` to intercept `https://tiles.openfreemap.org/styles/**` (deterministic minimal MapLibre v8 JSON referencing `"openmaptiles"` and OpenFreeMap attribution) and `https://tiles.openfreemap.org/fixture-tiles/**` (existing deterministic 256×256 PNG), with zero live external fetches.
2. Update `src/frontend/tooling/verify-maps.ts` with the same offline OpenFreeMap interception, assert zero requests to `https://tile.openstreetmap.org/**`, assert OpenFreeMap attribution links and `transformRequest` header isolation, exercise tile failure/retry on `"openmaptiles"` AND style-fetch failure/retry on `styles/**`, preserve the static subpath custom raster build test, and cover invalid `VITE_MAP_STYLE_URL` recovery alongside invalid `VITE_MAP_MAX_NATIVE_ZOOM`.
3. Update the comment in `src/frontend/tooling/snapshot-navigation.ts` line 3.
4. Run `task maps:verify` and `task snapshot:check -- --filter map-`; refresh any affected `map-*` visual baselines in `tests/frontend/snapshots/baselines/` and verify zero horizontal overflow at 375 px and 1440 px in both themes.

### Phase E: Documentation, Tracking & Quality Gates

1. Update `docs/operations/CONFIGURATION.md`, `docs/examples/.env.example`, `docs/architecture/DESIGN_FRONTEND.md`, `docs/specs/20261014-223122-open-source-explore-maps/TODO.md`, `docs/specs/index.md`, `docs/CHECKLIST.md`, and `docs/PLAN.md`.
2. Run all verification gates per [quickstart.md](quickstart.md): `task check`, `task test`, `task maps:verify`, `task snapshot:check`, and `task docs:check`.

## Complexity Tracking

No Constitution violations or justified complexity exceptions. The design adds zero new services, zero backend code, zero database migrations, and zero new npm/Python dependencies.
