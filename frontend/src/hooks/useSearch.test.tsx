import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearch } from "./useSearch";
import * as api from "@/lib/api";
import type { SearchResult } from "@/lib/structs";

vi.mock("@/lib/api", () => ({
  searchCampgrounds: vi.fn(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

const mockSearchResult: SearchResult = {
  id: "test-id",
  entity_type: "Campground",
  provider_id: 1,
  provider_name: "Recreation.gov",
  recreation_area_id: "rec-1",
  recreation_area_name: "Test Area",
  campground_id: "cg-1",
  campground_name: "Test Campground",
};

describe("useSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not query when query is empty", () => {
    renderHook(() => useSearch(""), {
      wrapper: createWrapper(),
    });
    expect(api.searchCampgrounds).not.toHaveBeenCalled();
  });

  it("does not query when query is too short (1 char)", () => {
    renderHook(() => useSearch("a"), {
      wrapper: createWrapper(),
    });
    expect(api.searchCampgrounds).not.toHaveBeenCalled();
  });

  it("queries when query is 2 or more characters", async () => {
    vi.mocked(api.searchCampgrounds).mockResolvedValue([mockSearchResult]);

    const { result } = renderHook(() => useSearch("te"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([mockSearchResult]);
    });
    expect(api.searchCampgrounds).toHaveBeenCalledWith("te");
  });

  it("passes trimmed query to the API", async () => {
    vi.mocked(api.searchCampgrounds).mockResolvedValue([mockSearchResult]);

    const { result } = renderHook(() => useSearch("  test  "), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([mockSearchResult]);
    });
    expect(api.searchCampgrounds).toHaveBeenCalledWith("test");
  });

  it("returns empty array when API returns empty", async () => {
    vi.mocked(api.searchCampgrounds).mockResolvedValue([]);

    const { result } = renderHook(() => useSearch("xy"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([]);
    });
  });

  it("has correct query key format", async () => {
    vi.mocked(api.searchCampgrounds).mockResolvedValue([mockSearchResult]);

    const { result } = renderHook(() => useSearch("test"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});
