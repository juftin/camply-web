import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SearchPage } from "./SearchPage";
import * as searchHook from "@/hooks/useSearch";
import type { SearchExploreResponse } from "@/lib/structs";

vi.mock("@/components/ScanForm", () => ({
  ScanForm: ({ trigger }: { trigger: React.ReactNode }) => (
    <div data-testid="scan-form-mock">{trigger}</div>
  ),
}));

const mockExploreData: SearchExploreResponse = {
  items: [
    {
      id: "Camp/1/1001/2001",
      entity_type: "Campground",
      provider_id: 1,
      provider_name: "recreation_dot_gov",
      recreation_area_id: "1001",
      recreation_area_name: "Yosemite National Park",
      campground_id: "2001",
      campground_name: "Upper Pines",
      city: "Yosemite Valley",
      state: "CA",
      country: "USA",
      latitude: 37.737,
      longitude: -119.565,
      reservable: true,
      campsite_types: ["TENT", "RV"],
      has_electric: true,
      has_water: false,
      has_sewer: false,
      pets_allowed: true,
      ada_accessible: true,
      max_rv_length: 35,
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
  facets: {
    providers: { recreation_dot_gov: 1 },
    states: { CA: 1 },
    entity_types: { Campground: 1 },
  },
};

function renderSearchPage(initialEntries = ["/search?q=Upper"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <SearchPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders search page title and campgrounds list", () => {
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: mockExploreData,
      isLoading: false,
      isFetching: false,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);

    renderSearchPage();

    expect(screen.getByText("Discover Campgrounds")).toBeInTheDocument();
    expect(screen.getByText("Upper Pines")).toBeInTheDocument();
    expect(screen.getByText(/Yosemite National Park/)).toBeInTheDocument();
    expect(screen.getByText("Electric")).toBeInTheDocument();
    expect(screen.getByText("Pets Allowed")).toBeInTheDocument();
    expect(screen.getByText("Monitor")).toBeInTheDocument();
  });

  it("renders empty state when no campgrounds match", () => {
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 1,
        facets: { providers: {}, states: {}, entity_types: {} },
      },
      isLoading: false,
      isFetching: false,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);

    renderSearchPage();

    expect(screen.getByText("No campgrounds found")).toBeInTheDocument();
  });

  it("renders loading state", () => {
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);

    renderSearchPage();

    expect(screen.getByText(/Searching campgrounds/i)).toBeInTheDocument();
  });
});
