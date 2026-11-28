---
description: "Dependency-ordered task list for OpenFreeMap Production Map Tiles (036)"
---

# Tasks: OpenFreeMap Production Map Tiles

**Input**: Design documents from `docs/specs/20261127-143403-openfreemap-production-tiles/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/map-basemap-config.md](contracts/map-basemap-config.md), [quickstart.md](quickstart.md)

**Tests**: Included per Constitution Principle V (test-first workflow: write/update failing tests before implementing each behavior).

**Organization**: Tasks are grouped by user story (`US1`–`US4`) so each increment can be implemented and independently verified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (`US1`, `US2`, `US3`, `US4`) — omitted for Setup, Foundational, and Polish phases
- Exact repository file paths are included in every task description

---

## Phase 1: Setup (Baseline Confirmation)

**Purpose**: Verify clean baseline test state before editing source or test files.

- [x] T001 Run existing map unit/component tests and packaging tests to confirm clean baseline (`pnpm exec vitest run src/frontend/lib/maps.test.ts src/frontend/components/MapComponent.test.tsx && uv run --all-extras -- pytest tests/test_frontend_build.py tests/test_compose.py -q`)

---

## Phase 2: Foundational (Types & Build-Arg Plumbing)

**Purpose**: Expose `VITE_MAP_STYLE_URL` to TypeScript, Hatchling packaging manifests, Docker image builds, and root Docker Compose so all user stories share consistent build-time plumbing.

**⚠️ CRITICAL**: Complete before User Story implementation begins.

- [x] T002 [P] Add `readonly VITE_MAP_STYLE_URL?: string;` to `ImportMetaEnv` in `src/frontend/vite-env.d.ts`
- [x] T003 [P] Add `"VITE_MAP_STYLE_URL"` to `PUBLIC_SETTINGS` in `src/hatchling/plugin.py` so Python wheel/sdist builds forward it to Vite and include it in `build/frontend-manifest.json` input digests
- [x] T004 [P] Add `ARG VITE_MAP_STYLE_URL` and `VITE_MAP_STYLE_URL=$VITE_MAP_STYLE_URL` to the `application-build` stage in `Dockerfile`
- [x] T005 [P] Forward `VITE_MAP_STYLE_URL: ${VITE_MAP_STYLE_URL:-}` under `x-camply.build.args` in `docker-compose.yaml`
- [x] T006 [P] Extend `test_manifest_records_only_supported_public_settings` in `tests/test_frontend_build.py` to assert `VITE_MAP_STYLE_URL` is captured in `manifest["settings"]` while unrelated `VITE_*` variables remain excluded
- [x] T007 [P] Add assertion in `tests/test_compose.py` verifying root `docker-compose.yaml` forwards `VITE_MAP_STYLE_URL` alongside `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_TEXT`, `VITE_MAP_ATTRIBUTION_URL`, and `VITE_MAP_MAX_NATIVE_ZOOM` in `build.args`

**Checkpoint**: Foundation ready — `uv run --all-extras -- pytest tests/test_frontend_build.py tests/test_compose.py -q` passes and `ImportMetaEnv` includes `VITE_MAP_STYLE_URL`.

---

## Phase 3: User Story 1 - Production-Ready Default Maps via OpenFreeMap Without Extra Infrastructure (Priority: P1) 🎯 MVP

**Goal**: Make all interactive maps (Explore, Campground detail, Recreation Area detail) default to OpenFreeMap's `liberty` vector style (`https://tiles.openfreemap.org/styles/liberty`) with zero API keys, zero requests to `tile.openstreetmap.org`, preserved `transformRequest` isolation, and MapLibre automatic attribution.

**Independent Test**: Run `pnpm exec vitest run src/frontend/lib/maps.test.ts src/frontend/components/MapComponent.test.tsx` and confirm empty env resolves to `{ kind: "style", styleUrl: "https://tiles.openfreemap.org/styles/liberty" }` and `MapComponent` passes that style URL string directly to `new LibreMap(...)` with `AttributionControl({ compact: false })` and `transformRequest` (`credentials: "same-origin"`, `referrerPolicy: "strict-origin"`).

### Tests for User Story 1 (Write First — Must Fail Before Implementation)

- [x] T008 [P] [US1] Update default basemap test in `src/frontend/lib/maps.test.ts` to expect `basemapConfig({})` (and `basemapConfig({ VITE_MAP_MAX_NATIVE_ZOOM: "19" })` as passed by Docker builds) to return `{ kind: "style", styleUrl: "https://tiles.openfreemap.org/styles/liberty" }` with zero references to `tile.openstreetmap.org`
- [x] T009 [P] [US1] Update default rendering test in `src/frontend/components/MapComponent.test.tsx` to assert `new LibreMap(...)` receives `style: "https://tiles.openfreemap.org/styles/liberty"`, `attributionControl: false`, `AttributionControl({ compact: false })`, and `transformRequest` returning `{ url, credentials: "same-origin", referrerPolicy: "strict-origin" }` without a `cache` override

### Implementation for User Story 1

- [x] T010 [US1] Export `DEFAULT_MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"`, `VectorStyleBasemapConfig`, `RasterTileBasemapConfig`, and discriminated union `BasemapConfig` in `src/frontend/lib/maps.ts`, updating `basemapConfig()` to return `{ kind: "style", styleUrl: DEFAULT_MAP_STYLE_URL }` by default when `VITE_MAP_TILE_URL` and `VITE_MAP_STYLE_URL` are unset or empty (depends on T002, T008)
- [x] T011 [US1] Update `src/frontend/components/MapComponent.tsx` to accept `BasemapConfig` and pass `config.styleUrl` directly as `style` to `new LibreMap(...)` when `config.kind === "style"`, relying on MapLibre's `AttributionControl({ compact: false })` for automatic style/TileJSON attribution (depends on T009, T010)

**Checkpoint**: User Story 1 (MVP) delivers production-safe OpenFreeMap defaults with zero infrastructure and passing unit/component tests.

---

## Phase 4: User Story 2 - Custom Vector Style and Backwards-Compatible Raster Tile Overrides (Priority: P1)

**Goal**: Support custom `VITE_MAP_STYLE_URL` overrides (HTTPS or same-origin root-relative paths), preserve full backwards compatibility for `VITE_MAP_TILE_URL` + `VITE_MAP_ATTRIBUTION_*` + `VITE_MAP_MAX_NATIVE_ZOOM` with raster taking explicit precedence, and strictly reject unsafe/malformed configurations locally.

**Independent Test**: Run `pnpm exec vitest run src/frontend/lib/maps.test.ts src/frontend/components/MapComponent.test.tsx` covering every row of the precedence matrix and every invalid URL/attribution/zoom rejection case in [data-model.md](data-model.md) and [contracts/map-basemap-config.md](contracts/map-basemap-config.md).

### Tests for User Story 2 (Write First — Must Fail Before Implementation)

- [x] T012 [P] [US2] Add unit tests in `src/frontend/lib/maps.test.ts` covering: custom HTTPS `VITE_MAP_STYLE_URL` (e.g. `https://tiles.openfreemap.org/styles/bright`), same-origin root-relative `VITE_MAP_STYLE_URL` (`/styles/liberty.json`), whitespace trimming / empty-string fallback to default, explicit precedence of `VITE_MAP_TILE_URL` over both default and `VITE_MAP_STYLE_URL`, rejection of invalid `VITE_MAP_STYLE_URL` (`http://...`, protocol-relative `//example.com/style.json`, `javascript:alert(1)`, `data:...`, relative path without leading `/`, whitespace inside URL, embedded credentials `https://user:pass@tiles.example/style.json`), and full backwards-compatible raster validation (required non-empty trimmed `VITE_MAP_ATTRIBUTION_TEXT`, valid `https://` `VITE_MAP_ATTRIBUTION_URL` without credentials, `{z}`/`{x}`/`{y}` tokens, integer `VITE_MAP_MAX_NATIVE_ZOOM` `0`–`19`)
- [x] T013 [P] [US2] Add component tests in `src/frontend/components/MapComponent.test.tsx` covering: custom `VITE_MAP_STYLE_URL` passed to `LibreMap`, custom `VITE_MAP_TILE_URL` override rendering the inline `version: 8` raster `StyleSpecification` with `tiles: [url]`, `maxzoom`, and safe DOM attribution anchor (`target="_blank"`, `rel="noopener noreferrer"`), and invalid `VITE_MAP_STYLE_URL` (e.g. `http://insecure.example/style.json` or `https://u:p@example.com/style.json`) showing a local `role="alert"` without instantiating `LibreMap`

### Implementation for User Story 2

- [x] T014 [US2] Implement complete precedence and strict validation in `basemapConfig()` in `src/frontend/lib/maps.ts`: trim inputs; when trimmed `VITE_MAP_TILE_URL` is non-empty select `kind: "raster"` (requiring non-empty trimmed `VITE_MAP_ATTRIBUTION_TEXT`, `https://` `VITE_MAP_ATTRIBUTION_URL` with empty `username`/`password`, `https://` or single-leading-`/` tile URL containing `{z}`, `{x}`, `{y}` with `protocol === "https:"` and empty `username`/`password`, and integer `VITE_MAP_MAX_NATIVE_ZOOM` `0`–`19` defaulting to `19`); otherwise resolve trimmed `VITE_MAP_STYLE_URL` or `DEFAULT_MAP_STYLE_URL` as `kind: "style"` (requiring `https://` or single-leading-`/` path without `//`, no ASCII whitespace/control characters, valid `new URL(styleUrl, "https://camply.invalid")` with `protocol === "https:"` and empty `username`/`password`) (depends on T010, T012)
- [x] T015 [US2] Ensure `src/frontend/components/MapComponent.tsx` cleanly dispatches `config.kind === "raster"` to the inline `StyleSpecification` with safe DOM `document.createElement("a")` attribution and `config.kind === "style"` to `config.styleUrl`, catching all `basemapConfig()` errors into local `error` state (depends on T011, T013, T014)

**Checkpoint**: User Stories 1 and 2 pass all Vitest unit and component checks for default vector style, custom vector style, custom raster overrides, precedence, and strict URL safety.

---

## Phase 5: User Story 3 - Resilient Basemap Failure Recovery and Legible Attribution Across Viewports & Themes (Priority: P2)

**Goal**: Handle transient tile errors from any vector or raster source identifier (e.g. `"openmaptiles"`, `"basemap"`, custom style source IDs) via non-blocking **Retry tiles**, handle remote style-load errors via local **Retry map**, and ensure multi-link OpenFreeMap attribution stays legible with zero horizontal overflow at 375 px mobile and 1440 px desktop in light and dark themes.

**Independent Test**: Run `pnpm exec vitest run src/frontend/components/MapComponent.test.tsx` to verify both `"openmaptiles"` and `"basemap"` tile retries plus style-fetch error recovery, and inspect attribution layout/contrast in light and dark themes at 375 px and 1440 px.

### Tests for User Story 3 (Write First — Must Fail Before Implementation)

- [x] T016 [P] [US3] Expand error-recovery tests in `src/frontend/components/MapComponent.test.tsx` to verify: (a) MapLibre `"error"` with `sourceId: "openmaptiles"` (vector source) shows non-blocking `Basemap tiles could not load` status and clicking **Retry tiles** calls `map.refreshTiles("openmaptiles")`, (b) MapLibre `"error"` with `sourceId: "basemap"` (custom raster source) still calls `map.refreshTiles("basemap")`, (c) multiple failing source IDs are all refreshed and cleared on retry, and (d) MapLibre `"error"` without `sourceId` (remote style JSON fetch failure) hides `Loading map…`, shows `role="alert"` with **Retry map**, and remounts `LibreMap` when clicked

### Implementation for User Story 3

- [x] T017 [US3] Generalize tile vs style error handling in `src/frontend/components/MapComponent.tsx`: add a `failedSources = useRef<Set<string>>(new Set())` ref; route any `"error"` event with non-empty string `event.sourceId` into `failedSources.current.add(event.sourceId)` and `setTileError(true)`; route `"error"` events without a non-empty `sourceId` into `setError(event.error?.message || "Map could not load.")`; update **Retry tiles** to clear `tileError`, call `map?.refreshTiles(id)` for every tracked source ID, and clear `failedSources.current`; clear `failedSources.current` on map remount/cleanup (depends on T015, T016)
- [x] T018 [US3] Review `.camply-map .maplibregl-ctrl-attrib` rules in `src/frontend/index.css` for multi-link OpenFreeMap attribution readability, contrast, and wrapping on 375 px mobile in light and dark themes; apply minimal CSS adjustments only if needed to prevent clipping or horizontal overflow (depends on T017)

**Checkpoint**: User Story 3 passes component error-recovery tests for vector/raster sources and style-load failures, with legible attribution styling.

---

## Phase 6: User Story 4 - Deterministic, Offline-Safe Automated Map Verification (Priority: P2)

**Goal**: Keep Playwright visual snapshots (`run-snapshots.ts`) and real browser map verification (`verify-maps.ts`) 100% offline and deterministic by intercepting `https://tiles.openfreemap.org/**` with local fixtures, asserting zero `tile.openstreetmap.org` traffic, verifying both source-tile retry and style-fetch retry, and refreshing any affected `map-*` visual baselines.

**Independent Test**: Run `task maps:verify` and `task snapshot:check -- --filter map-` and confirm zero live external map requests, zero `tile.openstreetmap.org` requests, zero horizontal overflow at 375 px / 1440 px light & dark, and passing visual comparisons.

### Implementation for User Story 4

- [x] T019 [P] [US4] Update `src/frontend/tooling/run-snapshots.ts` to intercept `https://tiles.openfreemap.org/styles/**` (returning a minimal deterministic MapLibre v8 JSON style with `"openmaptiles"` source pointing to `https://tiles.openfreemap.org/fixture-tiles/{z}/{x}/{y}.png` and OpenFreeMap/OpenMapTiles/OpenStreetMap attribution links) and `https://tiles.openfreemap.org/fixture-tiles/**` (returning the deterministic 256×256 `rgb(225, 235, 219)` PNG with `Access-Control-Allow-Origin: *`), replacing `https://tile.openstreetmap.org/**` interception and aborting/failing if any unexpected `tile.openstreetmap.org` request occurs
- [x] T020 [P] [US4] Update `src/frontend/tooling/verify-maps.ts` to: (a) intercept `https://tiles.openfreemap.org/styles/**` and `https://tiles.openfreemap.org/fixture-tiles/**` on all default pages (main, touch, WebGL-recovery), verifying zero `authorization`/`x-csrf-token` headers and origin-only `referer` pathname `/`, (b) assert zero requests to `https://tile.openstreetmap.org/**`, (c) verify visible OpenFreeMap/OpenStreetMap attribution links instead of legacy OSM-only attribution, (d) test both tile failure (`fixture-tiles/**` → **Retry tiles** on `"openmaptiles"`) and style JSON fetch failure (`styles/**` → **Retry map**), (e) preserve the static subpath custom raster `VITE_MAP_TILE_URL` build check, and (f) verify invalid `VITE_MAP_STYLE_URL` local error recovery alongside invalid `VITE_MAP_MAX_NATIVE_ZOOM`
- [x] T021 [P] [US4] Update the doc comment in `src/frontend/tooling/snapshot-navigation.ts` (line 3) from "raster tiles" to "basemap tiles" to match vector and raster basemaps
- [x] T022 [US4] Execute `task maps:verify` and confirm `tmp/maps-browser.json` reports zero `console_errors`, zero OSM requests, passing attribution/header/retry/override checks, and zero overflow at 375 px and 1440 px light/dark (depends on T017, T018, T020) — _Verified green in CI (`maps - browser verification`)_
- [x] T023 [US4] Run `task snapshot:check -- --filter map-` (or `task snapshot:docker -- --update --filter map-` if the updated OpenFreeMap attribution bar changes `map-*` pixels) and refresh/verify affected `map-*` baselines in `tests/frontend/snapshots/baselines/` with zero horizontal overflow (depends on T017, T018, T019, T021) — _Refreshed 24 map-bearing baselines from CI Playwright Docker captures with OpenFreeMap attribution_

**Checkpoint**: User Story 4 is complete — all Playwright browser and visual snapshot suites run 100% offline with zero live OpenFreeMap/OSM traffic.

---

## Phase 7: Polish, Documentation & Final Verification

**Purpose**: Update operator configuration, architecture, example env, spec index, roadmap, and feature checklist docs, then run full monorepo quality gates.

- [x] T024 [P] Update the **Maps (Public Frontend Build Settings)** section in `docs/operations/CONFIGURATION.md` to document `VITE_MAP_STYLE_URL` (default `https://tiles.openfreemap.org/styles/liberty`), custom `VITE_MAP_TILE_URL` raster precedence, build-time-only scope (no runtime endpoint), OpenFreeMap attribution/license/no-SLA/privacy notes, self-hosting alternatives, and CSP directives (`connect-src`, `img-src`, `worker-src`)
- [x] T025 [P] Update the commented map settings block in `docs/examples/.env.example` to include `# VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty` alongside the custom raster override variables
- [x] T026 [P] Update `docs/architecture/DESIGN_FRONTEND.md` (line 27) to reference `VITE_MAP_STYLE_URL` (OpenFreeMap vector default) alongside custom raster overrides (`VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_*`)
- [x] T027 [P] Update `docs/specs/20261014-223122-open-source-explore-maps/TODO.md` to note that production tile hosting (`T3.3.6`) is resolved via OpenFreeMap vector styles in `docs/specs/20261127-143403-openfreemap-production-tiles/`
- [x] T028 [P] Add feature `036: OpenFreeMap Production Map Tiles` with links to `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `research.md`, `contracts/map-basemap-config.md`, `quickstart.md`, and `checklists/requirements.md` in `docs/specs/index.md`
- [x] T029 [P] Update `T3.3.6` in `docs/CHECKLIST.md` to `[x]` with links to `specs/20261127-143403-openfreemap-production-tiles/spec.md` and `specs/20261127-143403-openfreemap-production-tiles/plan.md`, and update the **Map-Based Discovery** note in `docs/PLAN.md` to reflect the OpenFreeMap default
- [x] T030 Run full verification gates per [quickstart.md](quickstart.md): `task fix`, `task check`, `task test`, `uv run --all-extras -- pytest tests/docs/test_docs.py -q`, and `task docs:check` (depends on T022, T023, T024, T025, T026, T027, T028, T029; all locally executable gates passed, browser checks T022/T023 pending CI)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Starts immediately (`T001`).
- **Phase 2 (Foundational)**: Depends on `T001`. `T002`–`T007` touch distinct files and run in parallel. **Blocks** Phase 3+.
- **Phase 3 (US1 - MVP)**: Depends on Phase 2 (`T002`). `T008` and `T009` run in parallel (tests first), followed by `T010` → `T011`.
- **Phase 4 (US2)**: Depends on Phase 3 (`T010`, `T011`). `T012` and `T013` run in parallel (tests first), followed by `T014` → `T015`.
- **Phase 5 (US3)**: Depends on Phase 4 (`T015`). `T016` (tests first) → `T017` → `T018`.
- **Phase 6 (US4)**: `T019`, `T020`, `T021` can be authored in parallel; `T022` and `T023` execute once `T017`–`T021` are complete.
- **Phase 7 (Polish & Docs)**: `T024`–`T029` all touch distinct documentation files and run in parallel; `T030` runs final verification gates after everything is complete.

### Parallel Opportunities

```bash
# Phase 2 parallel batch (distinct files):
T002: src/frontend/vite-env.d.ts
T003: src/hatchling/plugin.py
T004: Dockerfile
T005: docker-compose.yaml
T006: tests/test_frontend_build.py
T007: tests/test_compose.py

# Phase 6 Playwright tooling parallel batch:
T019: src/frontend/tooling/run-snapshots.ts
T020: src/frontend/tooling/verify-maps.ts
T021: src/frontend/tooling/snapshot-navigation.ts

# Phase 7 documentation parallel batch:
T024: docs/operations/CONFIGURATION.md
T025: docs/examples/.env.example
T026: docs/architecture/DESIGN_FRONTEND.md
T027: docs/specs/20261014-223122-open-source-explore-maps/TODO.md
T028: docs/specs/index.md
T029: docs/CHECKLIST.md & docs/PLAN.md
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1 (`T001`) and Phase 2 (`T002`–`T007`) for types and build-arg plumbing.
2. Complete Phase 3 (`T008`–`T011`) and Phase 4 (`T012`–`T015`) to switch default maps to OpenFreeMap while keeping custom style and raster overrides 100% validated and backwards-compatible.
3. Validate with `pnpm exec vitest run src/frontend/lib/maps.test.ts src/frontend/components/MapComponent.test.tsx`.

### Full Production Hardening (User Story 3 + User Story 4 + Docs)

4. Complete Phase 5 (`T016`–`T018`) for multi-source tile retry, style-fetch retry, and mobile/dark attribution checks.
5. Complete Phase 6 (`T019`–`T023`) for offline Playwright verification (`task maps:verify`) and visual baselines (`task snapshot:check`).
6. Complete Phase 7 (`T024`–`T030`) for documentation updates and full CI-equivalent quality gates.

---

## Notes

- Total tasks: **30** (`T001`–`T030`).
- Zero backend runtime code, zero database migrations, and zero new infrastructure services are introduced.
- Visual baseline refresh (`T023`) should use `task snapshot:docker` when Docker is available so generated PNGs match CI pixel-for-pixel.
