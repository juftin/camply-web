import type { ReactNode } from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getScan, listScans } from "@/lib/api";
import { useScanDetail, useScans } from "./useScans";

vi.mock("@/lib/api", () => ({
  getScan: vi.fn(),
  listScans: vi.fn(),
}));

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

beforeEach(() => vi.clearAllMocks());

describe.each([
  { name: "scan list", useHook: () => useScans(), fetchScan: listScans },
  {
    name: "scan detail",
    useHook: () => useScanDetail("synthetic-scan"),
    fetchScan: getScan,
  },
])("$name authentication", ({ useHook, fetchScan }) => {
  it.each([401, 403])("does not retry HTTP %s", async (status) => {
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

  it("still retries a temporary failure once", async () => {
    vi.mocked(fetchScan).mockRejectedValue(new Error("Network unavailable"));

    const { result } = renderHook(() => useHook(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fetchScan).toHaveBeenCalledTimes(2);
  });
});
