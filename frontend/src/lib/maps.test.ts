import { describe, expect, it } from "vitest";
import {
  basemapConfig,
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
  it("supplies keyless defaults and rejects unsafe or misleading source configuration", () => {
    expect(basemapConfig({}).url).toBe(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    );
    expect(() =>
      basemapConfig({ VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png" }),
    ).toThrow(/attribution/i);
    expect(() => basemapConfig({ VITE_MAP_MAX_NATIVE_ZOOM: "20" })).toThrow();
    expect(() =>
      basemapConfig({ VITE_MAP_ATTRIBUTION_URL: "javascript:alert(1)" }),
    ).toThrow();
    expect(
      basemapConfig({
        VITE_MAP_TILE_URL: "/tiles/{z}/{x}/{y}.png",
        VITE_MAP_ATTRIBUTION_TEXT: "Fixture",
        VITE_MAP_ATTRIBUTION_URL: "https://example.com/license",
        VITE_MAP_MAX_NATIVE_ZOOM: "4",
      }).maxNativeZoom,
    ).toBe(4);
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
