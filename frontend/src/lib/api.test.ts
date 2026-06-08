import { describe, expect, it, vi, beforeEach } from "vitest";
import type { AxiosInstance } from "axios";

// We'll mock axios.create to return a controlled instance
const mockGet = vi.fn();
const mockAxiosInstance = {
  get: mockGet,
  defaults: {
    baseURL: "/api",
    timeout: 10000,
    headers: { "Content-Type": "application/json" },
  },
} as unknown as AxiosInstance;

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}));

describe("API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates an axios instance with correct config", async () => {
    const axiosMod = await import("axios");
    // Dynamic import triggers axios.create in the module
    await import("@/lib/api");
    expect(axiosMod.default.create).toHaveBeenCalled();
    const createCall = vi.mocked(axiosMod.default.create).mock.calls[0][0];
    expect(createCall).toBeDefined();
    expect(createCall!.baseURL).toBeDefined();
    expect(createCall!.timeout).toBeGreaterThan(0);
  });

  it("searchCampgrounds calls GET /search with correct params", async () => {
    mockGet.mockResolvedValue({
      data: [{ id: "1", entity_type: "Campground" }],
    });

    const api = await import("@/lib/api");
    const result = await api.searchCampgrounds("test", 10);
    expect(mockGet).toHaveBeenCalledWith("/search", {
      params: { query: "test", limit: 10 },
    });
    expect(result).toEqual([{ id: "1", entity_type: "Campground" }]);
  });

  it("searchCampgrounds returns empty array for empty query", async () => {
    const api = await import("@/lib/api");
    const result = await api.searchCampgrounds("");
    expect(result).toEqual([]);
  });

  it("getRecreationArea calls GET /rec-area/{provider}/{id}", async () => {
    mockGet.mockResolvedValue({
      data: { id: "rec-1", name: "Test Rec Area" },
    });

    const api = await import("@/lib/api");
    const result = await api.getRecreationArea(1, "rec-1");
    expect(mockGet).toHaveBeenCalledWith("/rec-area/1/rec-1");
    expect(result.name).toBe("Test Rec Area");
  });

  it("getProvider calls GET /provider/{id}", async () => {
    mockGet.mockResolvedValue({
      data: { id: 1, name: "Rec.gov" },
    });

    const api = await import("@/lib/api");
    const result = await api.getProvider(1);
    expect(mockGet).toHaveBeenCalledWith("/provider/1");
    expect(result.name).toBe("Rec.gov");
  });

  it("getCampgrounds calls GET /rec-area/{provider}/{id}/campgrounds", async () => {
    mockGet.mockResolvedValue({
      data: [{ id: "cg-1", name: "Test CG" }],
    });

    const api = await import("@/lib/api");
    const result = await api.getCampgrounds(1, "rec-1");
    expect(mockGet).toHaveBeenCalledWith("/rec-area/1/rec-1/campgrounds");
    expect(result).toEqual([{ id: "cg-1", name: "Test CG" }]);
  });

  it("getCampground calls GET /campground/{provider}/{id}", async () => {
    mockGet.mockResolvedValue({
      data: { id: "cg-1", name: "Test CG" },
    });

    const api = await import("@/lib/api");
    const result = await api.getCampground(1, "cg-1");
    expect(mockGet).toHaveBeenCalledWith("/campground/1/cg-1");
    expect(result.name).toBe("Test CG");
  });
});
