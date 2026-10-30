import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { SearchPage } from "./SearchPage";
import { mapQueryParams, type SearchExploreParams } from "@/lib/api";
import type { SavedMapView } from "@/components/ExploreMap";
import * as searchHook from "@/hooks/useSearch";
import type { SearchExploreResponse } from "@/lib/structs";

vi.mock("@/components/ScanForm", () => ({
  ScanForm: ({ trigger }: { trigger: React.ReactNode }) => (
    <div data-testid="scan-form-mock">{trigger}</div>
  ),
}));

vi.mock("@/components/ExploreMap", () => ({
  ExploreMap: ({
    saved,
    params,
    onSave,
    onViewport,
  }: {
    saved: SavedMapView | null;
    params: SearchExploreParams;
    onSave: (view: SavedMapView) => void;
    onViewport: (bounds: SavedMapView["bounds"], resetPage: boolean) => void;
  }) => (
    <div data-testid="explore-map" data-camera={JSON.stringify(saved?.camera)}>
      Map results
      <button
        onClick={() =>
          onViewport({ west: -106, east: -104, south: 34, north: 36 }, true)
        }
      >
        Zoom map
      </button>
      <button
        onClick={() =>
          onSave({
            context: JSON.stringify(mapQueryParams(params)),
            moved: true,
            camera: { lat: 35, lng: -105, zoom: 9 },
            bounds: { west: -106, east: -104, south: 34, north: 36 },
          })
        }
      >
        Pan map
      </button>
    </div>
  ),
}));
function LocationControls() {
  const location = useLocation(),
    navigate = useNavigate();
  return (
    <>
      <output data-testid="location">{location.search}</output>
      <button onClick={() => navigate(-1)}>Back</button>
    </>
  );
}
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

function HistoryControls() {
  const navigate = useNavigate();
  return (
    <>
      <button onClick={() => navigate(-1)}>Go back</button>
      <button onClick={() => navigate(1)}>Go forward</button>
    </>
  );
}

function renderSearchPage(initialEntries = ["/search?q=Upper"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <SearchPage />
        <HistoryControls />
        <LocationControls />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(searchHook, "useIpLocation").mockReturnValue({
      data: null,
      isPending: false,
    } as ReturnType<typeof searchHook.useIpLocation>);
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

  it.each(["", "&view=map", "&view=list", "&view=invalid"])(
    "starts with the map above the list without view controls (%s)",
    (legacyView) => {
      vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
        data: mockExploreData,
        isLoading: false,
        isFetching: false,
        error: null,
      } as unknown as ReturnType<typeof searchHook.useSearchExplore>);
      renderSearchPage([`/search?q=Upper${legacyView}`]);
      const map = screen.getByTestId("explore-map");
      const result = screen.getByRole("link", { name: "Upper Pines" });
      expect(map).toBeVisible();
      expect(result).toBeVisible();
      expect(map.compareDocumentPosition(result)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING,
      );
      expect(
        screen.queryByRole("group", { name: "Result view" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Map" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "List" }),
      ).not.toBeInTheDocument();
    },
  );

  it("collapses only the map and preserves its latest area and camera", () => {
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: { ...mockExploreData, total: 60, total_pages: 3 },
      isLoading: false,
      isFetching: false,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);
    renderSearchPage(["/search?q=Upper&page=2&state=CA"]);
    const toggle = screen.getByRole("button", { name: "Hide map" });
    const controlledId = toggle.getAttribute("aria-controls")!;
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(screen.getByRole("button", { name: "Pan map" }));
    fireEvent.click(toggle);
    expect(screen.queryByTestId("explore-map")).not.toBeInTheDocument();
    expect(document.getElementById(controlledId)).not.toBeVisible();
    expect(screen.getByRole("link", { name: "Upper Pines" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Monitor" })).toBeVisible();
    expect(screen.getByTestId("location")).toHaveTextContent(
      "?q=Upper&state=CA",
    );
    const show = screen.getByRole("button", { name: "Show map" });
    expect(show).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.queryByTestId("explore-map")).not.toBeInTheDocument();
    fireEvent.click(show);
    expect(screen.getByTestId("explore-map")).toBeVisible();
    expect(screen.getByTestId("explore-map")).toHaveAttribute(
      "data-camera",
      JSON.stringify({ lat: 35, lng: -105, zoom: 9 }),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("page=2");
  });

  it("keeps both representations through pagination and filter history", () => {
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: { ...mockExploreData, total: 60, total_pages: 3 },
      isLoading: false,
      isFetching: false,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);
    renderSearchPage(["/search?q=First&page=2", "/search?q=Second&page=2"]);
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByTestId("location")).toHaveTextContent("page=3");
    expect(screen.getByTestId("explore-map")).toBeVisible();
    expect(screen.getByRole("link", { name: "Upper Pines" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByPlaceholderText(/Search by campground/)).toHaveValue(
      "First",
    );
    expect(screen.getByTestId("location")).toHaveTextContent("page=2");
    expect(screen.getByTestId("explore-map")).toBeVisible();
    expect(screen.getByRole("link", { name: "Upper Pines" })).toBeVisible();
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

describe("live Explore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(searchHook, "useIpLocation").mockReturnValue({
      data: null,
      isPending: false,
    } as ReturnType<typeof searchHook.useIpLocation>);
    vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
      data: mockExploreData,
      isLoading: false,
      isFetching: false,
      error: null,
    } as unknown as ReturnType<typeof searchHook.useSearchExplore>);
  });

  it("filters and resets the full list on zoom while preserving bounds for sort and pagination", () => {
    vi.mocked(searchHook.useSearchExplore).mockReturnValue({
      data: { ...mockExploreData, total_pages: 3 },
      isLoading: false,
      isFetching: false,
    } as ReturnType<typeof searchHook.useSearchExplore>);
    renderSearchPage(["/search?q=Upper&page=3"]);
    fireEvent.click(screen.getByRole("button", { name: "Zoom map" }));
    const bounds = { west: -106, east: -104, south: 34, north: 36 };
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, bounds }),
      true,
    );
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, bounds }),
      true,
    );
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "name_asc" },
    });
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ sortBy: "name_asc", bounds }),
      true,
    );
    fireEvent.click(screen.getByRole("switch", { name: "Electric Hookups" }));
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ hasElectric: true, bounds: undefined }),
      true,
    );
  });

  it("starts unfiltered visits with the IP region, but leaves explicit searches alone", () => {
    vi.mocked(searchHook.useIpLocation).mockReturnValue({
      data: { lat: 35, lng: -105 },
      isPending: false,
    } as ReturnType<typeof searchHook.useIpLocation>);
    renderSearchPage(["/search"]);
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({
        bounds: { west: -108, east: -102, south: 33, north: 37 },
      }),
      true,
    );
  });

  it("falls back to broad discovery when the IP lookup fails", () => {
    renderSearchPage(["/search"]);
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ bounds: undefined }),
      true,
    );
    expect(screen.getByTestId("explore-map")).toBeVisible();
  });

  it("abandons pending location initialization when the visitor starts a search", () => {
    const lookup = vi
      .mocked(searchHook.useIpLocation)
      .mockReturnValue({ data: undefined, isPending: true } as ReturnType<
        typeof searchHook.useIpLocation
      >);
    renderSearchPage(["/search"]);
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.anything(),
      false,
    );
    expect(screen.queryByTestId("explore-map")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "Pines" },
    });
    lookup.mockReturnValue({
      data: { lat: 35, lng: -105 },
      isPending: false,
    } as ReturnType<typeof searchHook.useIpLocation>);
    fireEvent.click(screen.getByRole("button", { name: /^Search$/ }));
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "Pines", bounds: undefined }),
      true,
    );
  });

  it("skips IP initialization on explicit search links", () => {
    renderSearchPage(["/search?q=Upper&state=CA&page=2"]);
    expect(searchHook.useIpLocation).toHaveBeenLastCalledWith(false);
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({
        query: "Upper",
        state: "CA",
        page: 2,
        bounds: undefined,
      }),
      true,
    );
  });

  it("searches after typing without submitting and resets the page", async () => {
    vi.useFakeTimers();
    try {
      renderSearchPage(["/search?q=Upper&page=3"]);
      fireEvent.change(screen.getByPlaceholderText(/Search by campground/), {
        target: { value: "Pines" },
      });
      expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "Upper", page: 3 }),
        true,
      );
      await act(async () => {
        vi.advanceTimersByTime(300);
      });
      expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "Pines", page: 1 }),
        true,
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("applies filters to the pending query immediately", () => {
    renderSearchPage();
    fireEvent.change(screen.getByPlaceholderText(/Search by campground/), {
      target: { value: "Pines" },
    });
    fireEvent.click(screen.getByRole("switch", { name: "Electric Hookups" }));
    expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "Pines", hasElectric: true, page: 1 }),
      true,
    );
  });

  it("reset cancels pending typing and clears filters", async () => {
    vi.useFakeTimers();
    try {
      renderSearchPage(["/search?q=Upper&electric=true&page=2"]);
      fireEvent.change(screen.getByPlaceholderText(/Search by campground/), {
        target: { value: "Pines" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Reset" }));
      await act(async () => {
        vi.advanceTimersByTime(300);
      });
      expect(screen.getByPlaceholderText(/Search by campground/)).toHaveValue(
        "",
      );
      expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
        expect.objectContaining({
          query: undefined,
          hasElectric: undefined,
          page: 1,
        }),
        true,
      );
    } finally {
      vi.useRealTimers();
    }
  });
});

it("synchronizes the input with browser back and forward navigation", () => {
  vi.spyOn(searchHook, "useSearchExplore").mockReturnValue({
    data: mockExploreData,
    isLoading: false,
    isFetching: false,
    error: null,
  } as unknown as ReturnType<typeof searchHook.useSearchExplore>);
  renderSearchPage(["/search?q=Upper"]);
  const input = screen.getByRole("searchbox", { name: "Search campgrounds" });
  fireEvent.change(input, { target: { value: "Pines" } });
  fireEvent.click(screen.getByRole("button", { name: /^Search$/ }));
  fireEvent.click(screen.getByRole("button", { name: "Go back" }));
  expect(input).toHaveValue("Upper");
  expect(searchHook.useSearchExplore).toHaveBeenLastCalledWith(
    expect.objectContaining({ query: "Upper" }),
    true,
  );
  fireEvent.click(screen.getByRole("button", { name: "Go forward" }));
  expect(input).toHaveValue("Pines");
});
