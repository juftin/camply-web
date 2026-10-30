import { describe, expect, it, vi, beforeEach } from "vitest";
import { AxiosError, type AxiosInstance } from "axios";

// We'll mock axios.create to return a controlled instance
const mockGet = vi.fn();
const mockLocationGet = vi.hoisted(() => vi.fn());
const mockPost = vi.fn();
const mockUseFn = vi.fn();
const mockAxiosInstance = {
  get: mockGet,
  post: mockPost,
  interceptors: {
    request: { use: mockUseFn },
    response: { use: vi.fn() },
  },
  defaults: {
    baseURL: "/api",
    timeout: 10000,
    headers: { "Content-Type": "application/json" },
  },
} as unknown as AxiosInstance;

vi.mock("axios", async (importOriginal) => ({
  ...(await importOriginal<typeof import("axios")>()),
  default: {
    create: vi.fn(() => mockAxiosInstance),
    get: mockLocationGet,
  },
}));

describe("API Client", () => {
  it("uses an isolated bounded IP request and returns only valid coordinates", async () => {
    const { locateByIp } = await import("./api");
    const signal = new AbortController().signal;
    mockLocationGet.mockResolvedValue({ data: { latitude: 0, longitude: 0 } });
    expect(await locateByIp(signal)).toEqual({ lat: 0, lng: 0 });
    expect(mockLocationGet).toHaveBeenCalledWith("https://ipapi.co/json/", {
      signal,
      timeout: 2500,
      withCredentials: false,
      withXSRFToken: false,
    });
    for (const data of [
      { latitude: 91, longitude: 0 },
      { latitude: null, longitude: null },
      { latitude: 0, longitude: 0, error: true },
    ]) {
      mockLocationGet.mockResolvedValue({ data });
      expect(await locateByIp()).toBeNull();
    }
    mockLocationGet.mockRejectedValue(new Error("Timed out"));
    expect(await locateByIp()).toBeNull();
  });

  it("sends list bounds while keeping map context independent of that viewport", async () => {
    const { searchExplore, mapQueryParams } = await import("./api");
    mockGet.mockResolvedValue({ data: {} });
    const bounds = { west: 179, east: -179, south: -1, north: 1 };
    await searchExplore({ query: "Pines", bounds, page: 2 });
    expect(mockGet).toHaveBeenCalledWith("/search/explore", {
      params: { q: "Pines", page: 2, ...bounds },
      signal: undefined,
    });
    expect(mapQueryParams({ query: "Pines", bounds, page: 2 })).toEqual({
      q: "Pines",
    });
  });
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates an axios instance with correct config", async () => {
    vi.resetModules();
    const axiosMod = await import("axios");
    // Dynamic import triggers axios.create in the module
    await import("@/lib/api");
    expect(axiosMod.default.create).toHaveBeenCalled();
    const createCall = vi.mocked(axiosMod.default.create).mock.calls[0][0];
    expect(createCall).toBeDefined();
    expect(createCall!.baseURL).toBeDefined();
    expect(createCall!.timeout).toBeGreaterThan(0);
    expect(createCall!.withCredentials).toBe(true);
  });

  it("confirms the session cookie before returning a login profile", async () => {
    const profile = { id: "synthetic-user", email: "admin@example.com" };
    mockPost.mockResolvedValue({ data: profile });
    mockGet.mockResolvedValue({ data: profile });

    const api = await import("@/lib/api");
    expect(await api.loginSession("admin", "synthetic-password")).toEqual(
      profile,
    );
    expect(mockPost).toHaveBeenCalledWith("/login", {
      username: "admin",
      password: "synthetic-password",
    });
    expect(mockGet).toHaveBeenCalledWith("/me");
  });

  it("reports a rejected cookie instead of completing login", async () => {
    mockPost.mockResolvedValue({ data: { id: "synthetic-user" } });
    mockGet.mockRejectedValue(
      new AxiosError("Unauthorized", "ERR_BAD_REQUEST", undefined, undefined, {
        status: 401,
        data: { detail: "Sign in required" },
        statusText: "Unauthorized",
        headers: {},
        config: {} as never,
      }),
    );

    const api = await import("@/lib/api");
    await expect(
      api.loginSession("admin", "synthetic-password"),
    ).rejects.toThrow("session cookie");
  });

  it("preserves invalid credential errors without checking the session", async () => {
    const error = new AxiosError("Invalid username or password");
    mockPost.mockRejectedValue(error);

    const api = await import("@/lib/api");
    await expect(api.loginSession("admin", "wrong-password")).rejects.toBe(
      error,
    );
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("preserves temporary failures while checking the session", async () => {
    const error = new Error("Network unavailable");
    mockPost.mockResolvedValue({ data: { id: "synthetic-user" } });
    mockGet.mockRejectedValue(error);

    const api = await import("@/lib/api");
    await expect(api.loginSession("admin", "synthetic-password")).rejects.toBe(
      error,
    );
  });

  it("keeps map membership independent of list pagination/sort and forwards cancellation", async () => {
    const api = await import("@/lib/api");
    mockGet.mockResolvedValue({ data: {} });
    const signal = new AbortController().signal;
    const filters = {
      query: " Pines ",
      state: "CA",
      page: 3,
      pageSize: 20,
      sortBy: "name_desc",
      hasElectric: true,
    };
    await api.searchMapSummary(filters, signal);
    expect(mockGet).toHaveBeenLastCalledWith("/search/map/summary", {
      params: { q: "Pines", state: "CA", has_electric: true },
      signal,
    });
    const bounds = { west: 179, east: -179, south: -1, north: 1 };
    await api.searchMapMembers(
      filters,
      bounds,
      "1:0:0",
      "Camp/2/area/shared",
      signal,
    );
    expect(mockGet).toHaveBeenLastCalledWith("/search/map/members", {
      params: {
        q: "Pines",
        state: "CA",
        has_electric: true,
        ...bounds,
        cell_id: "1:0:0",
        after_id: "Camp/2/area/shared",
      },
      signal,
    });
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

it("attaches only a bearer token for application authentication", async () => {
  vi.resetModules();
  const api = await import("@/lib/api");
  api.setAccessTokenProvider(async () => "synthetic-access-token");
  const interceptor = mockUseFn.mock.calls[0][0];
  const request = await interceptor({ headers: {} });
  expect(request.headers.Authorization).toBe("Bearer synthetic-access-token");
});

it("forwards cancellation signals and filters to search transport", async () => {
  mockGet.mockResolvedValue({ data: [] });
  const api = await import("@/lib/api");
  const signal = new AbortController().signal;
  await api.searchExplore(
    { query: " Pines ", state: "CA", hasElectric: true, page: 2 },
    signal,
  );
  expect(mockGet).toHaveBeenLastCalledWith("/search/explore", {
    params: { q: "Pines", state: "CA", has_electric: true, page: 2 },
    signal,
  });
  await api.searchCampgrounds("Pines", 20, signal);
  expect(mockGet).toHaveBeenLastCalledWith("/search", {
    params: { query: "Pines", limit: 20 },
    signal,
  });
});
