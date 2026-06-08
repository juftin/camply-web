import { describe, expect, it } from "vitest";
import type {
  SearchResult,
  RecreationArea,
  Provider,
  Campground,
} from "./structs";

describe("SearchResult interface", () => {
  it("can be constructed with all fields", () => {
    const result: SearchResult = {
      id: "Campground/1/rec-1/cg-1",
      entity_type: "Campground",
      provider_id: 1,
      provider_name: "Recreation.gov",
      recreation_area_id: "rec-1",
      recreation_area_name: "Test Area",
      campground_id: "cg-1",
      campground_name: "Test Campground",
    };
    expect(result.id).toBe("Campground/1/rec-1/cg-1");
    expect(result.entity_type).toBe("Campground");
    expect(result.provider_id).toBe(1);
    expect(result.provider_name).toBe("Recreation.gov");
    expect(result.recreation_area_id).toBe("rec-1");
    expect(result.campground_id).toBe("cg-1");
  });

  it("can represent a RecreationArea entity type", () => {
    const result: SearchResult = {
      id: "RecreationArea/1/rec-1/",
      entity_type: "RecreationArea",
      provider_id: 1,
      provider_name: "Recreation.gov",
      recreation_area_id: "rec-1",
      recreation_area_name: "Yosemite National Park",
      campground_id: null,
      campground_name: null,
    };
    expect(result.entity_type).toBe("RecreationArea");
    expect(result.recreation_area_name).toBe("Yosemite National Park");
    expect(result.campground_id).toBeNull();
  });
});

describe("RecreationArea interface", () => {
  it("can be constructed with required fields", () => {
    const area: RecreationArea = {
      id: "rec-1",
      provider_id: 1,
      name: "Yosemite",
      description: null,
      country: null,
      state: null,
      longitude: null,
      latitude: null,
      reservable: true,
      enabled: true,
      url: "https://recreation.gov/...",
    };
    expect(area.name).toBe("Yosemite");
    expect(area.reservable).toBe(true);
    expect(area.url).toBeTruthy();
  });

  it("can have optional fields", () => {
    const area: RecreationArea = {
      id: "rec-2",
      provider_id: 1,
      name: "Test",
      description: "A nice area",
      country: "US",
      state: "CO",
      longitude: -105.0,
      latitude: 40.0,
      reservable: true,
      enabled: true,
      url: "https://example.com",
    };
    expect(area.country).toBe("US");
    expect(area.state).toBe("CO");
    expect(area.longitude).toBe(-105.0);
    expect(area.latitude).toBe(40.0);
  });
});

describe("Provider interface", () => {
  it("can be constructed with all fields", () => {
    const provider: Provider = {
      id: 1,
      name: "Recreation.gov",
      description: "Federal recreation portal",
      url: "https://recreation.gov",
      enabled: true,
    };
    expect(provider.id).toBe(1);
    expect(provider.enabled).toBe(true);
  });
});

describe("Campground interface", () => {
  it("can be constructed with all fields", () => {
    const campground: Campground = {
      id: "cg-1",
      provider_id: 1,
      recreation_area_id: "rec-1",
      name: "Test CG",
      description: "A test campground",
      country: "US",
      state: "CA",
      longitude: -119.0,
      latitude: 37.0,
      reservable: true,
      enabled: true,
      url: "https://recreation.gov/...",
    };
    expect(campground.name).toBe("Test CG");
    expect(campground.reservable).toBe(true);
    expect(campground.url).toBeTruthy();
  });
});
