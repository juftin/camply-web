import { describe, expect, it } from "vitest";
import {
  DEFAULT_MAP_STYLE_URL,
  basemapConfig,
  hasMappableCoordinates,
  regionalBounds,
  validCoordinates,
  normalizeLongitude,
  viewportBounds,
  fitLocations,
  toCampground,
} from "./maps";

describe("map geometry and configuration", () => {
  it("keeps IP regional bounds valid across the dateline and near the poles", () => {
    expect(regionalBounds(0, 179)).toEqual({
      west: 176,
      east: -178,
      south: -2,
      north: 2,
    });
    expect(regionalBounds(89, 0)).toEqual({
      west: -3,
      east: 3,
      south: 87,
      north: 90,
    });
  });

  it("accepts zero and poles while rejecting missing, nonfinite and invalid coordinates", () => {
    expect(validCoordinates(0, 0)).toBe(true);
    expect(validCoordinates(90, 180)).toBe(true);
    for (const latitude of [null, undefined, NaN, Infinity, 91])
      expect(validCoordinates(latitude, 0)).toBe(false);
    expect(validCoordinates(0, -181)).toBe(false);
  });
  it("filters out items that have a lat/lon of 0/0 from mappable coordinates", () => {
    expect(hasMappableCoordinates({ latitude: 0, longitude: 0 })).toBe(false);
    expect(hasMappableCoordinates({ latitude: 0, longitude: 10 })).toBe(true);
    expect(hasMappableCoordinates({ latitude: 10, longitude: 0 })).toBe(true);
    expect(hasMappableCoordinates({ latitude: null, longitude: 0 })).toBe(
      false,
    );
    expect(hasMappableCoordinates(null)).toBe(false);
  });
  it("frames dateline neighbors on the shortest arc", () => {
    expect(normalizeLongitude(540)).toBe(-180);
    const bounds = fitLocations([
      { lat: 1, lng: 179 },
      { lat: 2, lng: -179 },
    ]);
    expect(bounds).toEqual({ west: 179, east: -179, south: 1, north: 2 });
    expect(viewportBounds(-190, -86, 190, 86)).toEqual({
      west: -180,
      east: 180,
      south: -90,
      north: 90,
    });
  });
  it("defaults to OpenFreeMap liberty vector style with zero OSM references", () => {
    const defaultConfig = basemapConfig({});
    expect(defaultConfig).toEqual({
      kind: "style",
      styleUrl: DEFAULT_MAP_STYLE_URL,
    });
    expect(DEFAULT_MAP_STYLE_URL).toBe(
      "https://tiles.openfreemap.org/styles/liberty",
    );
    expect(JSON.stringify(defaultConfig)).not.toContain(
      "tile.openstreetmap.org",
    );
    expect(basemapConfig({ VITE_MAP_MAX_NATIVE_ZOOM: "19" })).toEqual({
      kind: "style",
      styleUrl: DEFAULT_MAP_STYLE_URL,
    });
    expect(
      basemapConfig({
        VITE_MAP_STYLE_URL: "   ",
        VITE_MAP_TILE_URL: "  ",
        VITE_MAP_MAX_NATIVE_ZOOM: "25",
        VITE_MAP_ATTRIBUTION_URL: "javascript:alert(1)",
      }),
    ).toEqual({
      kind: "style",
      styleUrl: DEFAULT_MAP_STYLE_URL,
    });
  });

  it("supports custom vector styles, raster precedence, and rejects unsafe basemap configuration", () => {
    expect(
      basemapConfig({
        VITE_MAP_STYLE_URL: "  https://tiles.openfreemap.org/styles/bright  ",
      }),
    ).toEqual({
      kind: "style",
      styleUrl: "https://tiles.openfreemap.org/styles/bright",
    });
    expect(
      basemapConfig({ VITE_MAP_STYLE_URL: "/styles/liberty.json" }),
    ).toEqual({
      kind: "style",
      styleUrl: "/styles/liberty.json",
    });

    for (const invalidStyleUrl of [
      "http://insecure.example/style.json",
      "//example.com/style.json",
      "javascript:alert(1)",
      "data:application/json,{}",
      "styles/liberty.json",
      "https://tiles.example.test/styles/bad style.json",
      "https://tiles.example.test/styles/line\nbreak.json",
      "https://user:pass@tiles.example/style.json",
      "https://:pass@tiles.example/style.json",
      "https://[invalid",
    ]) {
      expect(() =>
        basemapConfig({ VITE_MAP_STYLE_URL: invalidStyleUrl }),
      ).toThrow(/style/i);
    }

    expect(
      basemapConfig({
        VITE_MAP_STYLE_URL: "https://tiles.openfreemap.org/styles/bright",
        VITE_MAP_TILE_URL: " /tiles/{z}/{x}/{y}.png ",
        VITE_MAP_ATTRIBUTION_TEXT: " Fixture ",
        VITE_MAP_ATTRIBUTION_URL: " https://example.com/license ",
        VITE_MAP_MAX_NATIVE_ZOOM: "4",
      }),
    ).toEqual({
      kind: "raster",
      url: "/tiles/{z}/{x}/{y}.png",
      text: "Fixture",
      link: "https://example.com/license",
      maxNativeZoom: 4,
    });
    expect(
      basemapConfig({
        VITE_MAP_TILE_URL: "https://tiles.example.test/{z}/{x}/{y}.png",
        VITE_MAP_ATTRIBUTION_TEXT: "Example Tiles",
        VITE_MAP_ATTRIBUTION_URL: "https://example.test/license",
      }),
    ).toEqual({
      kind: "raster",
      url: "https://tiles.example.test/{z}/{x}/{y}.png",
      text: "Example Tiles",
      link: "https://example.test/license",
      maxNativeZoom: 19,
    });
    expect(
      basemapConfig({
        VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png",
        VITE_MAP_ATTRIBUTION_TEXT: "Min Zoom",
        VITE_MAP_ATTRIBUTION_URL: "https://example.test/license",
        VITE_MAP_MAX_NATIVE_ZOOM: "0",
      }),
    ).toMatchObject({ kind: "raster", maxNativeZoom: 0 });

    expect(() =>
      basemapConfig({ VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png" }),
    ).toThrow(/attribution/i);
    expect(() =>
      basemapConfig({
        VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png",
        VITE_MAP_ATTRIBUTION_TEXT: "   ",
        VITE_MAP_ATTRIBUTION_URL: "https://example.com/license",
      }),
    ).toThrow(/attribution/i);
    for (const invalidAttrUrl of [
      "http://example.com/license",
      "javascript:alert(1)",
      "https://user:pass@example.com/license",
      "https://[invalid",
    ]) {
      expect(() =>
        basemapConfig({
          VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png",
          VITE_MAP_ATTRIBUTION_TEXT: "Fixture",
          VITE_MAP_ATTRIBUTION_URL: invalidAttrUrl,
        }),
      ).toThrow();
    }
    for (const invalidTileUrl of [
      "http://insecure.example/{z}/{x}/{y}.png",
      "//example.com/{z}/{x}/{y}.png",
      "javascript:bad",
      "/tiles/{z}/{x}.png",
      "https://user:pass@tiles.example/{z}/{x}/{y}.png",
      "https://[invalid/{z}/{x}/{y}.png",
    ]) {
      expect(() =>
        basemapConfig({
          VITE_MAP_TILE_URL: invalidTileUrl,
          VITE_MAP_ATTRIBUTION_TEXT: "Fixture",
          VITE_MAP_ATTRIBUTION_URL: "https://example.com/license",
        }),
      ).toThrow();
    }
    for (const invalidZoom of ["20", "25", "-1", "14.5", "abc", "Infinity"]) {
      expect(() =>
        basemapConfig({
          VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png",
          VITE_MAP_ATTRIBUTION_TEXT: "Fixture",
          VITE_MAP_ATTRIBUTION_URL: "https://example.com/license",
          VITE_MAP_MAX_NATIVE_ZOOM: invalidZoom,
        }),
      ).toThrow(/native zoom/i);
    }
  });
  it("preserves zeros and exact provider identity when prefilling a scan", () => {
    const result = toCampground({
      id: "Camp/2/area/place",
      entity_type: "Campground",
      provider_id: 2,
      provider_name: "Fixture",
      campground_id: "place",
      recreation_area_id: "area",
      campground_name: "Place",
      recreation_area_name: "Area",
      latitude: 0,
      longitude: 0,
    });
    expect(result).toMatchObject({
      id: "place",
      provider_id: 2,
      latitude: 0,
      longitude: 0,
    });
  });
});
