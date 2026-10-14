# Open-Source Maps: Production Tile Hosting & Caching TODO

## Background

The map surfaces (Explore, Campground detail, and Recreation Area detail) default to OpenStreetMap's public raster tile server (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).

While this default provides an immediate, zero-credential development experience and automated tests intercept requests with synthetic fixtures, OpenStreetMap's [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) establishes that:
- Public tile servers are operated on community donations with strict capacity limits.
- High-volume, public, or automated production traffic must not rely directly on `tile.openstreetmap.org`.
- Bulk downloading and pre-rendering are prohibited.

Before launching high-traffic public production releases, configure an appropriate hosted, cached, or self-hosted tile backend.

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

- [ ] Select preferred production tile strategy (Managed SaaS, Cloudflare Cache, or PMTiles).
- [ ] Configure `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION_TEXT`, `VITE_MAP_ATTRIBUTION_URL`, and `VITE_MAP_MAX_NATIVE_ZOOM` in production deployment pipeline (Cloudflare Pages environment secrets / Docker build arguments).
- [ ] Verify that custom attribution text and links render cleanly at 375px mobile and 1440px desktop viewports.
- [ ] Verify that map zoom levels and max native zoom behave properly without blurry or missing tile errors.
