# Quickstart & Validation Guide: OpenFreeMap Production Map Tiles

**Feature**: `20261127-143403-openfreemap-production-tiles`  
**Related**: [spec.md](spec.md) | [plan.md](plan.md) | [data-model.md](data-model.md) | [contracts/map-basemap-config.md](contracts/map-basemap-config.md)

Use these runnable validation scenarios to verify the OpenFreeMap default basemap, custom style and raster override precedence, error recovery, build/packaging forwarding, offline browser verification, and documentation hygiene.

---

## Prerequisites

Install backend and frontend dependencies from the repository root:

```bash
task install
```

---

## Scenario 1: Frontend Unit & Component Tests

Verify basemap precedence, URL/attribution/zoom validation, OpenFreeMap default style initialization, custom raster fallback, multi-source tile retry (`openmaptiles` and `basemap`), and style-fetch failure recovery:

```bash
pnpm exec vitest run src/frontend/lib/maps.test.ts src/frontend/components/MapComponent.test.tsx
```

**Expected outcome**:

- All assertions pass with zero skipped tests.
- Default `basemapConfig({})` resolves to `{ kind: "style", styleUrl: "https://tiles.openfreemap.org/styles/liberty" }`.
- Setting `VITE_MAP_TILE_URL` takes precedence over both the default and `VITE_MAP_STYLE_URL`.
- Unsafe style/tile URLs (`http://`, `//...`, `javascript:`, embedded credentials) throw descriptive validation errors and keep `MapComponent` error alerts local without instantiating MapLibre.
- Non-`"basemap"` source errors (`sourceId: "openmaptiles"`) trigger `tileError` and call `refreshTiles("openmaptiles")` on **Retry tiles**; style errors without `sourceId` trigger `role="alert"` + **Retry map**.

---

## Scenario 2: Packaging, Hatchling Manifest & Docker Compose Wiring

Verify that Python packaging (`src/hatchling/plugin.py`) forwards and digests `VITE_MAP_STYLE_URL` and that `docker-compose.yaml` stays valid:

```bash
uv run --all-extras -- pytest tests/test_frontend_build.py tests/test_compose.py -q
```

**Expected outcome**:

- `manifest["settings"]` records `VITE_MAP_STYLE_URL` when set while excluding unrelated `VITE_*` variables.
- All Compose flavor validations pass.

---

## Scenario 3: Real Browser Map Verification (Offline-Safe)

Exercise real MapLibre GL JS rendering, header/referrer isolation, OpenFreeMap attribution links, zero `tile.openstreetmap.org` requests, `"openmaptiles"` tile retry, style-fetch retry, custom raster static subpath build, invalid style/zoom recovery, and 375 px / 1440 px light & dark layouts:

```bash
task maps:verify
```

**Expected outcome**:

- Exits 0 and writes `tmp/maps-browser.json` with zero `console_errors`.
- Zero live requests reach `tiles.openfreemap.org` or `tile.openstreetmap.org`.
- Both 375 px mobile and 1440 px desktop viewports in light and dark modes report zero document-level horizontal overflow (`scrollWidth <= innerWidth`) and visible attribution links.
- Custom raster static subpath build (`/map-check/`) and invalid config checks pass.

---

## Scenario 4: Visual Regression Snapshots (Offline-Safe)

Verify visual snapshots for all map views using offline OpenFreeMap fixtures:

```bash
task snapshot:check -- --filter map-
```

If OpenFreeMap's updated attribution pill (`OpenFreeMap © OpenMapTiles Data from OpenStreetMap`) intentionally updates the `map-*` baselines, refresh and inspect them in the CI-matched Playwright container (or locally if Chromium system libraries are installed):

```bash
task snapshot:docker -- --update --filter map-
task snapshot:report
```

**Expected outcome**:

- Every `map-*` scenario settles cleanly to `data-map-idle="true"` with zero external map traffic.
- Inspect the generated gallery report to confirm crisp, non-overlapping attribution on 375 px mobile and 1440 px desktop in both light and dark themes.

---

## Scenario 5: Manual Live Dev Server Smoke Check (Optional, Requires Internet)

Confirm live OpenFreeMap vector tiles and custom overrides in a local browser:

```bash
# 1. Default OpenFreeMap liberty style (zero env vars)
task frontend:dev

# 2. Alternate OpenFreeMap style override
VITE_MAP_STYLE_URL="https://tiles.openfreemap.org/styles/bright" task frontend:dev

# 3. Backwards-compatible custom raster override
VITE_MAP_TILE_URL="https://tile.openstreetmap.org/{z}/{x}/{y}.png" \
VITE_MAP_ATTRIBUTION_TEXT="© OpenStreetMap contributors" \
VITE_MAP_ATTRIBUTION_URL="https://www.openstreetmap.org/copyright" \
task frontend:dev
```

Open `/search` and inspect browser DevTools Network tab:

- Mode 1 fetches `https://tiles.openfreemap.org/styles/liberty` (zero requests to `tile.openstreetmap.org`) and renders crisp vector cartography with linked OpenFreeMap / OpenMapTiles / OpenStreetMap attribution.
- Mode 2 fetches `https://tiles.openfreemap.org/styles/bright`.
- Mode 3 fetches the configured raster XYZ tiles and displays only the configured custom attribution link.

---

## Scenario 6: Full Quality Gates & Documentation Validation

Run the repository-wide formatting, linting, type checking, test, and documentation checks before opening a PR:

```bash
task check
task test
uv run --all-extras -- pytest tests/docs/test_docs.py -q
task docs:check
```

**Expected outcome**:

- `task check` (`ruff`, `oxlint`, `oxfmt`, `mypy`, `tsc`, Import Linter) passes with zero warnings/errors.
- `task test` passes across backend, packaging, release, frontend, and Pages suites.
- `tests/docs/test_docs.py` and `task docs:check` pass with zero broken links or editorial violations.
