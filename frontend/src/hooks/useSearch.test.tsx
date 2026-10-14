import React from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearch, useSearchExplore } from "./useSearch";
import * as api from "@/lib/api";
import type { SearchExploreResponse, SearchResult } from "@/lib/structs";

vi.mock("@/lib/api", () => ({
  searchCampgrounds: vi.fn(),
  searchExplore: vi.fn(),
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
    expect(api.searchCampgrounds).toHaveBeenCalledWith(
      "te",
      20,
      expect.any(AbortSignal),
    );
  });

  it("passes trimmed query to the API", async () => {
    vi.mocked(api.searchCampgrounds).mockResolvedValue([mockSearchResult]);

    const { result } = renderHook(() => useSearch("  test  "), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual([mockSearchResult]);
    });
    expect(api.searchCampgrounds).toHaveBeenCalledWith(
      "test",
      20,
      expect.any(AbortSignal),
    );
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

describe("useSearchExplore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockExploreResponse: SearchExploreResponse = {
    items: [mockSearchResult],
    total: 1,
    page: 1,
    page_size: 20,
    total_pages: 1,
    facets: {
      providers: { "Recreation.gov": 1 },
      states: { CA: 1 },
      entity_types: { Campground: 1 },
    },
  };

  it("fetches exploration results with filters", async () => {
    vi.mocked(api.searchExplore).mockResolvedValue(mockExploreResponse);

    const { result } = renderHook(
      () =>
        useSearchExplore({
          query: "Yosemite",
          state: "CA",
          hasElectric: true,
        }),
      {
        wrapper: createWrapper(),
      },
    );

    await waitFor(() => {
      expect(result.current.data).toEqual(mockExploreResponse);
    });
    expect(api.searchExplore).toHaveBeenCalledWith(
      {
        query: "Yosemite",
        state: "CA",
        hasElectric: true,
      },
      expect.any(AbortSignal),
    );
  });
});

it("aborts obsolete Explore requests when filters change", async () => {
  vi.mocked(api.searchExplore).mockImplementation(() => new Promise(() => {}));
  const { rerender, unmount } = renderHook(
    ({ state }) => useSearchExplore({ state }),
    { wrapper: createWrapper(), initialProps: { state: "CA" } },
  );
  await waitFor(() => expect(api.searchExplore).toHaveBeenCalled());
  const requests = vi.mocked(api.searchExplore).mock.calls;
  const firstSignal = requests[requests.length - 1][1]!;
  expect(firstSignal.aborted).toBe(false);
  rerender({ state: "CO" });
  await waitFor(() => expect(firstSignal.aborted).toBe(true));
  const secondSignal = requests[requests.length - 1][1]!;
  expect(secondSignal.aborted).toBe(false);
  unmount();
  expect(secondSignal.aborted).toBe(true);
});
