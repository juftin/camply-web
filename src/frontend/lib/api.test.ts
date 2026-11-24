import { describe, expect, it, vi, beforeEach } from "vitest";
import { AxiosError, type AxiosInstance } from "axios";

// We'll mock axios.create to return a controlled instance
const mockGet = vi.fn();
const mockLocationGet = vi.hoisted(() => vi.fn());
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();
const mockRequest = vi.fn();
const mockUseFn = vi.fn();
const mockResponseUseFn = vi.fn();
const mockAxiosInstance = Object.assign(mockRequest, {
  get: mockGet,
  post: mockPost,
  patch: mockPatch,
  delete: mockDelete,
  request: mockRequest,
  interceptors: {
    request: { use: mockUseFn },
    response: { use: mockResponseUseFn },
  },
  defaults: {
    baseURL: "/api",
    timeout: 10000,
    headers: { "Content-Type": "application/json" },
  },
}) as unknown as AxiosInstance;

vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<typeof import("axios")>();
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => mockAxiosInstance),
      get: mockLocationGet,
    },
  };
});

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

it("calls admin access request endpoints with typed params and payload", async () => {
  mockGet.mockResolvedValue({ data: { access_requests: [], total: 0 } });
  mockPatch.mockResolvedValue({ data: { id: "req-1", status: "approved" } });
  const api = await import("@/lib/api");

  await api.listAdminAccessRequests({
    status: "pending",
    search: "camper",
    limit: 25,
    offset: 0,
  });
  expect(mockGet).toHaveBeenLastCalledWith("/admin/access-requests", {
    params: { status: "pending", search: "camper", limit: 25, offset: 0 },
  });

  await api.updateAdminAccessRequest("req-1", { status: "approved" });
  expect(mockPatch).toHaveBeenLastCalledWith("/admin/access-requests/req-1", {
    status: "approved",
  });
});

it("lists and revokes active password sessions for the current user", async () => {
  const sessionList = {
    items: [
      {
        id: "sess-1",
        user_agent: "Mozilla/5.0",
        ip_address: "198.51.100.1",
        created_at: "2026-11-15T10:00:00Z",
        expires_at: "2026-11-22T10:00:00Z",
        is_current: true,
      },
    ],
  };
  mockGet.mockResolvedValue({ data: sessionList });
  mockDelete.mockResolvedValue({ data: undefined });

  const api = await import("@/lib/api");
  expect(await api.listMySessions()).toEqual(sessionList);
  expect(mockGet).toHaveBeenLastCalledWith("/me/sessions");

  await api.revokeMySession("sess-1");
  expect(mockDelete).toHaveBeenLastCalledWith("/me/sessions/sess-1");
});

describe("Token acquisition classification and bounded 401 renewal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function makeAxiosHttpError(
    status: number,
    method = "GET",
    data: Record<string, unknown> = {},
    retried?: boolean,
  ): AxiosError {
    const config = {
      url: "/me",
      method,
      headers: {},
      ...(retried ? { _retried: true } : {}),
    } as never;
    return new AxiosError(
      `HTTP ${status}`,
      "ERR_BAD_REQUEST",
      config,
      undefined,
      {
        status,
        data,
        statusText: `Status ${status}`,
        headers: {},
        config,
      },
    );
  }

  it("classifies expired, outage, and auth_failure token acquisition errors", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");

    for (const code of [
      "login_required",
      "consent_required",
      "interaction_required",
      "missing_refresh_token",
      "invalid_grant",
    ]) {
      const classified = api.classifyTokenAcquisitionError({ error: code });
      expect(classified).toBeInstanceOf(api.TokenAcquisitionError);
      expect(classified.kind).toBe("expired");
      expect(classified.code).toBe(code);
    }

    for (const err of [
      new TypeError("Failed to fetch"),
      new Error("NetworkError when attempting to fetch resource."),
      Object.assign(new Error("Request timeout"), { name: "TimeoutError" }),
      { status: 503, message: "IdP 503" },
    ]) {
      const classified = api.classifyTokenAcquisitionError(err);
      expect(classified.kind).toBe("outage");
    }

    const denied = api.classifyTokenAcquisitionError({
      error: "access_denied",
      error_description: "User denied access",
    });
    expect(denied.kind).toBe("auth_failure");
    expect(denied.message).toBe("User denied access");

    const invalidScope = api.classifyTokenAcquisitionError({
      error: "invalid_scope",
    });
    expect(invalidScope.kind).toBe("auth_failure");
  });

  it("propagates classified token errors from request interceptor instead of dropping auth", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");
    const onSessionExpired = vi.fn();
    const onOutage = vi.fn();
    const onAuthFailure = vi.fn();

    const provider = vi
      .fn()
      .mockRejectedValueOnce({ error: "login_required" })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce({ error: "access_denied" });
    api.setAccessTokenProvider(provider, {
      onSessionExpired,
      onOutage,
      onAuthFailure,
    });

    const requestInterceptor = mockUseFn.mock.calls.at(-1)?.[0];

    await expect(requestInterceptor({ headers: {} })).rejects.toMatchObject({
      name: "TokenAcquisitionError",
      kind: "expired",
    });
    expect(onSessionExpired).toHaveBeenCalledTimes(1);

    await expect(requestInterceptor({ headers: {} })).rejects.toMatchObject({
      name: "TokenAcquisitionError",
      kind: "outage",
    });
    expect(onOutage).toHaveBeenCalledTimes(1);

    await expect(requestInterceptor({ headers: {} })).rejects.toMatchObject({
      name: "TokenAcquisitionError",
      kind: "auth_failure",
    });
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });

  it("renews a token once with cacheMode=off for safe idempotent 401s and deduplicates concurrent refreshes", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");
    const onSessionExpired = vi.fn();
    const provider = vi.fn().mockResolvedValue("refreshed-access-token");

    api.setApiAuthMode("auth0");
    api.setAccessTokenProvider(provider, { onSessionExpired });
    mockRequest.mockResolvedValue({ data: { ok: true } });

    const responseErrorHandler = mockResponseUseFn.mock.calls.at(-1)?.[1];
    const [res1, res2] = await Promise.all([
      responseErrorHandler(makeAxiosHttpError(401, "GET")),
      responseErrorHandler(makeAxiosHttpError(401, "HEAD")),
    ]);

    expect(res1).toEqual({ data: { ok: true } });
    expect(res2).toEqual({ data: { ok: true } });
    expect(provider).toHaveBeenCalledTimes(1);
    expect(provider).toHaveBeenCalledWith({ cacheMode: "off" });
    expect(mockRequest).toHaveBeenCalledTimes(2);
    expect(onSessionExpired).not.toHaveBeenCalled();
  });

  it("does not loop if the retried safe request still returns 401", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");
    const onSessionExpired = vi.fn();
    const provider = vi.fn();

    api.setApiAuthMode("auth0");
    api.setAccessTokenProvider(provider, { onSessionExpired });

    const responseErrorHandler = mockResponseUseFn.mock.calls.at(-1)?.[1];
    await expect(
      responseErrorHandler(makeAxiosHttpError(401, "GET", {}, true)),
    ).rejects.toBeInstanceOf(AxiosError);

    expect(provider).not.toHaveBeenCalled();
    expect(mockRequest).not.toHaveBeenCalled();
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
  });

  it.each(["POST", "PUT", "PATCH", "DELETE"])(
    "never replays unsafe %s mutations on 401",
    async (method) => {
      vi.resetModules();
      const api = await import("@/lib/api");
      const onSessionExpired = vi.fn();
      const provider = vi.fn().mockResolvedValue("should-not-be-requested");

      api.setApiAuthMode("auth0");
      api.setAccessTokenProvider(provider, { onSessionExpired });

      const responseErrorHandler = mockResponseUseFn.mock.calls.at(-1)?.[1];
      await expect(
        responseErrorHandler(makeAxiosHttpError(401, method)),
      ).rejects.toBeInstanceOf(AxiosError);

      expect(provider).not.toHaveBeenCalled();
      expect(mockRequest).not.toHaveBeenCalled();
      expect(onSessionExpired).toHaveBeenCalledTimes(1);
      expect(onSessionExpired.mock.calls[0][0].kind).toBe("expired");
    },
  );

  it("routes 401 renewal failures by classification without calling onSessionExpired on outages", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");
    const onSessionExpired = vi.fn();
    const onOutage = vi.fn();
    const provider = vi
      .fn()
      .mockRejectedValueOnce({ error: "missing_refresh_token" })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));

    api.setApiAuthMode("auth0");
    api.setAccessTokenProvider(provider, { onSessionExpired, onOutage });

    const responseErrorHandler = mockResponseUseFn.mock.calls.at(-1)?.[1];

    await expect(
      responseErrorHandler(makeAxiosHttpError(401, "GET")),
    ).rejects.toMatchObject({ kind: "expired" });
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
    expect(onOutage).not.toHaveBeenCalled();

    await expect(
      responseErrorHandler(makeAxiosHttpError(401, "OPTIONS")),
    ).rejects.toMatchObject({ kind: "outage" });
    expect(onOutage).toHaveBeenCalledTimes(1);
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
    expect(mockRequest).not.toHaveBeenCalled();
  });

  it("does not trigger Auth0 renewal in session mode or for 403/409/503 responses", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");
    const onSessionExpired = vi.fn();
    const provider = vi.fn();

    api.setApiAuthMode("session");
    api.setAccessTokenProvider(provider, { onSessionExpired });
    const responseErrorHandler = mockResponseUseFn.mock.calls.at(-1)?.[1];

    await expect(
      responseErrorHandler(makeAxiosHttpError(401, "GET")),
    ).rejects.toBeInstanceOf(AxiosError);

    api.setApiAuthMode("auth0");
    for (const status of [403, 409, 503]) {
      await expect(
        responseErrorHandler(makeAxiosHttpError(status, "GET")),
      ).rejects.toBeInstanceOf(AxiosError);
    }

    expect(provider).not.toHaveBeenCalled();
    expect(onSessionExpired).not.toHaveBeenCalled();
  });

  it("formats 403, 409, 503, and TokenAcquisitionError messages clearly", async () => {
    vi.resetModules();
    const api = await import("@/lib/api");

    expect(
      api.getApiErrorMessage(
        makeAxiosHttpError(403, "GET", {
          detail: {
            code: "ERR_VERIFIED_EMAIL_REQUIRED",
            message: "Verified email address is required.",
          },
        }),
      ),
    ).toBe("Verified email address is required.");

    expect(
      api.getApiErrorMessage(
        makeAxiosHttpError(409, "GET", {
          detail: {
            code: "ERR_EMAIL_CONFLICT",
            message: "This email is already linked to another login.",
          },
        }),
      ),
    ).toBe("This email is already linked to another login.");

    expect(api.getApiErrorMessage(makeAxiosHttpError(503, "GET", {}))).toMatch(
      /temporarily unavailable/i,
    );

    expect(
      api.getApiErrorMessage(
        new api.TokenAcquisitionError("outage", "IdP down"),
      ),
    ).toBe("IdP down");
  });
});
