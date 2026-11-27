# Open-Source Maps: Production Tile Hosting & Caching TODO

> **Resolved**: Production tile hosting (`T3.3.6`) is resolved by defaulting all interactive maps to OpenFreeMap vector styles (`https://tiles.openfreemap.org/styles/liberty` via `VITE_MAP_STYLE_URL`) while keeping backwards-compatible custom raster overrides (`VITE_MAP_TILE_URL` + `VITE_MAP_ATTRIBUTION_*`). See [OpenFreeMap Production Map Tiles](../20261127-143403-openfreemap-production-tiles/spec.md) and its [implementation plan](../20261127-143403-openfreemap-production-tiles/plan.md).

## Background

Previously, the map surfaces (Explore, Campground detail, and Recreation Area detail) defaulted to OpenStreetMap's public raster tile server (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).

While that default provided an immediate, zero-credential development experience and automated tests intercepted requests with synthetic fixtures, OpenStreetMap's [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) establishes that:

- Public tile servers are operated on community donations with strict capacity limits.
- High-volume, public, or automated production traffic must not rely directly on `tile.openstreetmap.org`.
- Bulk downloading and pre-rendering are prohibited.

Default builds now use OpenFreeMap vector tiles at $0/month with zero additional infrastructure; operators with strict SLA or air-gapped requirements can still configure an alternate vector style (`VITE_MAP_STYLE_URL`) or custom raster XYZ backend (`VITE_MAP_TILE_URL`).

---

## Production Tile Options

The application consumes standard XYZ raster tiles (`EPSG:3857`) configured via build-time frontend environment variables (`VITE_MAP_*`).

### Option 1: Managed Open-Source Tile Provider (Fastest)

Register with a tile provider supporting standard XYZ raster endpoints (many provide free tiers suitable for community projects):

- **MapTiler**: Free tier (100k requests/month). Standard 256px raster XYZ endpoint:
  ```bash
  VITE_MAP_TILE_URL="https://api.maptiler.com/maps/basic-v2/256/{z}/{x}/{y}.png?key=YOUR_API_KEY"
  VITE_MAP_ATTRIBUTION_TEXT="© MapTiler © OpenStreetMap contributors"
  VITE_MAP_ATTRIBUTION_URL="https://www.maptiler.com/copyright/"
  VITE_MAP_MAX_NATIVE_ZOOM=19
  ```
- **Stadia Maps**: Keyed XYZ raster endpoint with attribution.

### Option 2: Cloudflare Reverse Proxy & Caching (Recommended for Cloudflare Pages)

Since the frontend is deployed to Cloudflare Pages, set up a Cloudflare Worker or caching rule to cache OpenStreetMap tiles at the edge:

- Map tiles are immutable and can be safely cached with `Cache-Control: public, max-age=2592000` (30 days).
- Configure a route such as `/tiles/{z}/{x}/{y}.png` forwarding to OpenStreetMap with a custom `User-Agent` per OSM policy, achieving >95% cache hit rates.
- Set build args:
  ```bash
  VITE_MAP_TILE_URL="/tiles/{z}/{x}/{y}.png"
  VITE_MAP_ATTRIBUTION_TEXT="© OpenStreetMap contributors"
  VITE_MAP_ATTRIBUTION_URL="https://www.openstreetmap.org/copyright"
  ```

### Option 3: Self-Hosted PMTiles / Vector Tiles (Zero External Dependency)

- Host an open-source [PMTiles](https://protomaps.com/) archive (e.g. North America or Planet extract) in Cloudflare R2 or an S3 bucket.
- Serve via an edge serverless function or containerized tile server ([Martin](https://martin.maplibre.org/)).
- Retain standard OSM copyright and attribution.

---

## Implementation Checklist

- [x] Select preferred production tile strategy (OpenFreeMap vector styles by default; Managed SaaS, reverse-proxy cache, or self-hosted PMTiles supported via `VITE_MAP_STYLE_URL` / `VITE_MAP_TILE_URL` — see [OpenFreeMap Production Map Tiles](../20261127-143403-openfreemap-production-tiles/spec.md)).
- [x] Forward `VITE_MAP_STYLE_URL`, `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_TEXT`, `VITE_MAP_ATTRIBUTION_URL`, and `VITE_MAP_MAX_NATIVE_ZOOM` across frontend builds, Hatchling packaging, and Docker/Compose build arguments.
- [x] Verify that attribution text and links render cleanly at 375px mobile and 1440px desktop viewports with zero horizontal overflow.
- [x] Verify that vector styles and custom raster max native zoom behave properly with local retry recovery on tile and style failures.
