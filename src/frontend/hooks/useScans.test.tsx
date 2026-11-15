import type { ReactNode } from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getScan, listScans, TokenAcquisitionError } from "@/lib/api";
import { useScanDetail, useScans } from "./useScans";

const mockAuthState = vi.hoisted(() => ({
  isReady: true,
  user: {
    id: "user-1",
    email: "user@example.test",
    is_invited: true,
    is_admin: false,
    scanning_enabled: true,
    pushover_token: null,
  } as {
    id: string;
    email: string;
    is_invited: boolean;
    is_admin: boolean;
    scanning_enabled: boolean;
    pushover_token: string | null;
  } | null,
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getScan: vi.fn(),
    listScans: vi.fn(),
  };
});

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 1, retryDelay: 0 } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockAuthState.isReady = true;
  mockAuthState.user = {
    id: "user-1",
    email: "user@example.test",
    is_invited: true,
    is_admin: false,
    scanning_enabled: true,
    pushover_token: null,
  };
});

describe.each([
  { name: "scan list", useHook: () => useScans(), fetchScan: listScans },
  {
    name: "scan detail",
    useHook: () => useScanDetail("synthetic-scan"),
    fetchScan: getScan,
  },
])("$name authentication", ({ useHook, fetchScan }) => {
  it.each([401, 403, 409])("does not retry HTTP %s", async (status) => {
    const error = new AxiosError(
      "Access denied",
      "ERR_BAD_REQUEST",
      undefined,
      undefined,
      {
        status,
        data: {},
        statusText: "Access denied",
        headers: {},
        config: {} as never,
      },
    );
    vi.mocked(fetchScan).mockRejectedValue(error);

    const { result } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchScan).toHaveBeenCalledTimes(1);
  });

  it.each(["expired", "auth_failure"] as const)(
    "does not retry %s token acquisition failures",
    async (kind) => {
      vi.mocked(fetchScan).mockRejectedValue(
        new TokenAcquisitionError(kind, "Token failure"),
      );

      const { result } = renderHook(() => useHook(), {
        wrapper: createWrapper(),
      });
      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(fetchScan).toHaveBeenCalledTimes(1);
    },
  );

  it("retries transient outage token errors once", async () => {
    vi.mocked(fetchScan).mockRejectedValue(
      new TokenAcquisitionError("outage", "IdP unreachable"),
    );

    const { result } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchScan).toHaveBeenCalledTimes(2);
  });

  it("retries HTTP 503 verification-service outages once", async () => {
    vi.mocked(fetchScan).mockRejectedValue(
      new AxiosError(
        "Service Unavailable",
        "ERR_BAD_RESPONSE",
        undefined,
        undefined,
        {
          status: 503,
          data: { detail: "JWKS unreachable" },
          statusText: "Service Unavailable",
          headers: {},
          config: {} as never,
        },
      ),
    );

    const { result } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchScan).toHaveBeenCalledTimes(2);
  });

  it("still retries a temporary failure once", async () => {
    vi.mocked(fetchScan).mockRejectedValue(new Error("Network unavailable"));

    const { result } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchScan).toHaveBeenCalledTimes(2);
  });

  it("waits until auth is ready and user is authenticated before querying", async () => {
    mockAuthState.isReady = false;
    mockAuthState.user = null;
    vi.mocked(fetchScan).mockResolvedValue({} as never);

    const { result, rerender } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(fetchScan).not.toHaveBeenCalled();

    mockAuthState.isReady = true;
    rerender();
    expect(fetchScan).not.toHaveBeenCalled();

    mockAuthState.user = {
      id: "user-1",
      email: "user@example.test",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
    };
    rerender();

    await waitFor(() => expect(fetchScan).toHaveBeenCalledTimes(1));
  });
});
