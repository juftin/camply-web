import { type ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { AxiosRequestConfig, AxiosResponse } from "axios";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthConfigContext, AuthProvider, useAuth } from "./useAuth";
import { useScans } from "./useScans";
import { useAdminOverview } from "./useAdmin";
import { createScan, type AuthConfig } from "@/lib/api";

const mockAdapter = vi.hoisted(() => vi.fn());

const auth0 = vi.hoisted(() => ({
  isAuthenticated: false,
  isLoading: false,
  user: undefined as { sub?: string } | undefined,
  error: undefined as Error | undefined,
  getAccessTokenSilently: vi.fn(),
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => auth0,
}));

vi.mock("axios", async (importOriginal) => {
  const actual = await importOriginal<typeof import("axios")>();
  const originalCreate = actual.default.create.bind(actual.default);
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn((config?: Parameters<typeof actual.default.create>[0]) => {
        const instance = originalCreate(config);
        instance.defaults.adapter = (reqConfig) => mockAdapter(reqConfig);
        return instance;
      }),
    },
  };
});

const auth0Config: AuthConfig = {
  auth_mode: "auth0",
  auth0_domain: "test.example.com",
  auth0_client_id: "test-client",
  auth0_audience: "https://api.example.com",
  invite_only: false,
  auto_login: false,
  signup_enabled: true,
};

function makeAxiosResponse<T>(
  data: T,
  config: AxiosRequestConfig,
  status = 200,
): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: "OK",
    headers: {},
    config: config as never,
  };
}

function makeAxiosError(
  status: number,
  config: AxiosRequestConfig,
  data: Record<string, unknown> = {},
): AxiosError {
  return new AxiosError(
    `HTTP ${status}`,
    status >= 500 ? "ERR_BAD_RESPONSE" : "ERR_BAD_REQUEST",
    config as never,
    undefined,
    {
      status,
      data,
      statusText: `HTTP ${status}`,
      headers: {},
      config: config as never,
    },
  );
}

function createHarness(config: AuthConfig = auth0Config) {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retryDelay: 0,
      },
    },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthConfigContext.Provider value={config}>
        <AuthProvider>{children}</AuthProvider>
      </AuthConfigContext.Provider>
    </QueryClientProvider>
  );
  return { client, Wrapper };
}

function authHeader(config: AxiosRequestConfig): string | undefined {
  const headers = config.headers as
    | { get?: (name: string) => unknown; Authorization?: string }
    | undefined;
  if (headers && typeof headers.get === "function") {
    const val = headers.get("Authorization");
    return typeof val === "string" ? val : undefined;
  }
  return headers?.Authorization;
}

describe("useAuth Auth0 token lifecycle & session recovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    auth0.isAuthenticated = true;
    auth0.isLoading = false;
    auth0.user = { sub: "auth0|user-a" };
    auth0.error = undefined;
    auth0.getAccessTokenSilently.mockResolvedValue("synthetic-token-a");
  });

  it("waits until auth is ready and authenticated before firing protected scan/admin queries", async () => {
    auth0.isLoading = true;
    auth0.isAuthenticated = false;
    auth0.user = undefined;

    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "admin-1",
            email: "admin@example.test",
            is_invited: true,
            is_admin: true,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      if (config.url === "/scans") {
        return makeAxiosResponse({ scans: [], total: 0 }, config);
      }
      if (config.url === "/admin/overview") {
        return makeAxiosResponse({ total_users: 1 }, config);
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    const { Wrapper } = createHarness();
    const { result, rerender } = renderHook(
      () => ({
        auth: useAuth(),
        scans: useScans(),
        admin: useAdminOverview(),
      }),
      { wrapper: Wrapper },
    );

    expect(result.current.auth.isReady).toBe(false);
    expect(mockAdapter).not.toHaveBeenCalled();

    auth0.isLoading = false;
    auth0.isAuthenticated = true;
    auth0.user = { sub: "auth0|admin-1" };
    rerender();

    await waitFor(() => expect(result.current.auth.isReady).toBe(true));
    await waitFor(() => expect(result.current.scans.isSuccess).toBe(true));
    await waitFor(() => expect(result.current.admin.isSuccess).toBe(true));

    expect(mockAdapter.mock.calls.map(([c]) => c.url)).toEqual([
      "/me",
      "/scans",
      "/admin/overview",
    ]);
  });

  it("renews an expired Auth0 token once on a safe GET 401 and succeeds on retry", async () => {
    let scanCalls = 0;
    auth0.getAccessTokenSilently
      .mockResolvedValueOnce("stale-token")
      .mockResolvedValueOnce("stale-token")
      .mockResolvedValueOnce("fresh-token");

    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "user-a",
            email: "a@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      if (config.url === "/scans") {
        scanCalls += 1;
        if (scanCalls === 1) {
          throw makeAxiosError(401, config, { detail: "Token expired" });
        }
        return makeAxiosResponse(
          { scans: [{ id: "scan-1" }], total: 1 },
          config,
        );
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    const { Wrapper } = createHarness();
    const { result } = renderHook(
      () => ({ auth: useAuth(), scans: useScans() }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.scans.isSuccess).toBe(true));
    expect(result.current.scans.data).toEqual({
      scans: [{ id: "scan-1" }],
      total: 1,
    });
    expect(scanCalls).toBe(2);
    expect(auth0.getAccessTokenSilently).toHaveBeenCalledWith({
      cacheMode: "off",
    });
    expect(authHeader(mockAdapter.mock.calls[2][0])).toBe("Bearer fresh-token");
    expect(result.current.auth.user?.id).toBe("user-a");
    expect(result.current.auth.error).toBeNull();
  });

  it("clears protected caches and requires sign-in without looping when 401 renewal fails", async () => {
    let scanCalls = 0;
    auth0.getAccessTokenSilently.mockImplementation(
      async (opts?: { cacheMode?: string }) => {
        if (opts?.cacheMode === "off") {
          throw Object.assign(new Error("Login required"), {
            error: "login_required",
          });
        }
        return "stale-token";
      },
    );

    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "user-a",
            email: "a@example.test",
            is_invited: true,
            is_admin: true,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      if (config.url === "/scans") {
        scanCalls += 1;
        throw makeAxiosError(401, config, { detail: "Session revoked" });
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    const { client, Wrapper } = createHarness();
    client.setQueryData(["admin", "overview"], { total_users: 99 });

    const { result } = renderHook(
      () => ({ auth: useAuth(), scans: useScans() }),
      { wrapper: Wrapper },
    );

    await waitFor(() =>
      expect(result.current.auth.error).toMatch(/session has expired/i),
    );
    expect(result.current.auth.user).toBeNull();
    expect(scanCalls).toBe(1);
    expect(client.getQueryCache().findAll({ queryKey: ["scans"] })).toEqual([]);
    expect(client.getQueryCache().findAll({ queryKey: ["admin"] })).toEqual([]);
    expect(auth0.loginWithRedirect).not.toHaveBeenCalled();
  });

  it("never automatically replays unsafe POST mutations on 401 and requires re-auth", async () => {
    let postCalls = 0;
    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "user-a",
            email: "a@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      if (config.url === "/scans" && config.method?.toLowerCase() === "post") {
        postCalls += 1;
        throw makeAxiosError(401, config, { detail: "Expired" });
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    const { Wrapper } = createHarness();
    const { result } = renderHook(() => useAuth(), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.user?.id).toBe("user-a"));

    await act(async () => {
      await expect(
        createScan({
          provider_id: 1,
          campground_id: "232447",
          start_date: "2026-07-01",
          end_date: "2026-07-03",
          min_stay_length: 2,
        }),
      ).rejects.toBeInstanceOf(AxiosError);
    });

    expect(postCalls).toBe(1);
    expect(auth0.getAccessTokenSilently).not.toHaveBeenCalledWith({
      cacheMode: "off",
    });
    await waitFor(() =>
      expect(result.current.error).toMatch(/session expired/i),
    );
    expect(result.current.user).toBeNull();
  });

  it("surfaces 503 verification-service outages and IdP network outages without clearing the session", async () => {
    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "user-a",
            email: "a@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      if (config.url === "/scans") {
        throw makeAxiosError(503, config, {
          detail: "JWKS verification endpoint unavailable",
        });
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    const { Wrapper } = createHarness();
    const { result } = renderHook(
      () => ({ auth: useAuth(), scans: useScans() }),
      { wrapper: Wrapper },
    );

    await waitFor(() => expect(result.current.scans.isError).toBe(true));
    expect(result.current.auth.user?.id).toBe("user-a");
    expect(auth0.logout).not.toHaveBeenCalled();

    // Subsequent IdP network outage on a protected refetch keeps the user signed in
    // and surfaces a distinct temporary outage error rather than forcing sign-out.
    auth0.getAccessTokenSilently.mockRejectedValue(
      new TypeError("Failed to fetch"),
    );
    let refetchResult:
      | Awaited<ReturnType<typeof result.current.scans.refetch>>
      | undefined;
    await act(async () => {
      refetchResult = await result.current.scans.refetch();
    });
    expect(refetchResult?.error).toMatchObject({
      name: "TokenAcquisitionError",
      kind: "outage",
    });
    expect(result.current.auth.user?.id).toBe("user-a");
    expect(result.current.auth.error).toBeNull();
  });

  it.each([
    {
      status: 403,
      code: "ERR_VERIFIED_EMAIL_REQUIRED",
      message: "Verified email address is required.",
    },
    {
      status: 403,
      code: "ERR_INVITE_REQUIRED",
      message: "An invitation is required to access camply.",
    },
    {
      status: 409,
      code: "ERR_EMAIL_CONFLICT",
      message: "This email is already linked to another account.",
    },
  ])(
    "surfaces HTTP $status ($code) on /me without retry loops",
    async ({ status, code, message }) => {
      let meCalls = 0;
      mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
        if (config.url === "/me") {
          meCalls += 1;
          throw makeAxiosError(status, config, {
            detail: { code, message },
          });
        }
        throw new Error(`Unexpected request: ${config.url}`);
      });

      const { Wrapper } = createHarness();
      const { result } = renderHook(() => useAuth(), { wrapper: Wrapper });

      await waitFor(() => expect(result.current.isReady).toBe(true));
      expect(result.current.user).toBeNull();
      expect(result.current.error).toBe(message);
      expect(meCalls).toBe(1);
    },
  );

  it("clears cached user, scan, and admin data on account switch and sign-out, with zero token leakage", async () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    try {
      mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
        if (config.url === "/me") {
          const token = authHeader(config);
          if (token === "Bearer synthetic-token-b") {
            return makeAxiosResponse(
              {
                id: "user-b",
                email: "b@example.test",
                is_invited: true,
                is_admin: false,
                scanning_enabled: true,
                pushover_token: null,
              },
              config,
            );
          }
          return makeAxiosResponse(
            {
              id: "user-a",
              email: "a@example.test",
              is_invited: true,
              is_admin: true,
              scanning_enabled: true,
              pushover_token: null,
            },
            config,
          );
        }
        if (config.url === "/scans") {
          const token = authHeader(config);
          return makeAxiosResponse(
            {
              scans: [
                {
                  id:
                    token === "Bearer synthetic-token-b"
                      ? "scan-user-b"
                      : "scan-user-a",
                },
              ],
              total: 1,
            },
            config,
          );
        }
        throw new Error(`Unexpected request: ${config.url}`);
      });

      const { client, Wrapper } = createHarness();
      const { result, rerender } = renderHook(
        () => ({ auth: useAuth(), scans: useScans() }),
        { wrapper: Wrapper },
      );

      await waitFor(() =>
        expect(result.current.scans.data?.scans[0]?.id).toBe("scan-user-a"),
      );
      client.setQueryData(["admin", "users"], [{ id: "secret-admin-data" }]);

      // Simulate Auth0 account switch from user A to user B
      auth0.user = { sub: "auth0|user-b" };
      auth0.getAccessTokenSilently.mockResolvedValue("synthetic-token-b");
      rerender();

      await waitFor(() => expect(result.current.auth.user?.id).toBe("user-b"));
      await waitFor(() =>
        expect(result.current.scans.data?.scans[0]?.id).toBe("scan-user-b"),
      );
      expect(client.getQueryCache().findAll({ queryKey: ["admin"] })).toEqual(
        [],
      );

      // Sign out clears user, scan, and admin caches
      await act(async () => {
        await result.current.auth.signOut();
      });

      expect(auth0.logout).toHaveBeenCalledTimes(1);
      expect(client.getQueryData(["me"])).toBeNull();
      expect(client.getQueryCache().findAll({ queryKey: ["scans"] })).toEqual(
        [],
      );
      expect(client.getQueryCache().findAll({ queryKey: ["admin"] })).toEqual(
        [],
      );

      expect(localStorage.length).toBe(0);
      expect(sessionStorage.length).toBe(0);
      const loggedText = [
        ...consoleSpy.mock.calls,
        ...warnSpy.mock.calls,
        ...errorSpy.mock.calls,
      ]
        .flat()
        .join(" ");
      expect(loggedText).not.toContain("synthetic-token-a");
      expect(loggedText).not.toContain("synthetic-token-b");
    } finally {
      consoleSpy.mockRestore();
      warnSpy.mockRestore();
      errorSpy.mockRestore();
    }
  });

  it("handles page reload / new tab in-memory renewal success and fallback login_required cleanly", async () => {
    mockAdapter.mockImplementation(async (config: AxiosRequestConfig) => {
      if (config.url === "/me") {
        return makeAxiosResponse(
          {
            id: "user-a",
            email: "a@example.test",
            is_invited: true,
            is_admin: false,
            scanning_enabled: true,
            pushover_token: null,
          },
          config,
        );
      }
      throw new Error(`Unexpected request: ${config.url}`);
    });

    // Fresh QueryClient simulates a full page reload or second tab with empty in-memory cache.
    const tab1 = createHarness();
    const hook1 = renderHook(() => useAuth(), { wrapper: tab1.Wrapper });
    await waitFor(() => expect(hook1.result.current.user?.id).toBe("user-a"));
    hook1.unmount();

    // Tab 2 / reload where third-party cookies / silent iframe fail with login_required.
    auth0.getAccessTokenSilently.mockRejectedValueOnce({
      error: "login_required",
    });
    const tab2 = createHarness();
    const hook2 = renderHook(() => useAuth(), { wrapper: tab2.Wrapper });

    await waitFor(() => expect(hook2.result.current.isReady).toBe(true));
    expect(hook2.result.current.user).toBeNull();
    expect(hook2.result.current.error).toMatch(/session has expired/i);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(auth0.loginWithRedirect).not.toHaveBeenCalled();
  });
});
