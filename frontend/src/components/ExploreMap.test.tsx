import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ExploreMap } from "./ExploreMap";
import * as hooks from "@/hooks/useSearch";
import type { MapPin, GeoBounds, MapCamera } from "@/lib/maps";
vi.mock("@/hooks/useSearch", () => ({
  useMapSummary: vi.fn(),
  useMapFeatures: vi.fn(),
  useMapMembers: vi.fn(),
}));
vi.mock("./MapComponent", () => ({
  MapComponent: ({
    pins,
    onMove,
    bounds,
    camera,
  }: {
    pins: MapPin[];
    bounds?: GeoBounds;
    camera?: MapCamera | null;
    onMove: (bounds: GeoBounds, camera: MapCamera, initial?: boolean) => void;
  }) => (
    <div
      data-testid="map-canvas"
      data-camera={JSON.stringify(camera)}
      data-bounds={JSON.stringify(bounds)}
    >
      <button
        onClick={() =>
          onMove(
            { west: -106, east: -104, south: 34, north: 36 },
            { lat: 35, lng: -105, zoom: 9 },
          )
        }
      >
        Move map
      </button>
      <button
        onClick={() =>
          onMove(
            { west: -106, east: -104, south: 34, north: 36 },
            { lat: 35, lng: -105, zoom: 9 },
            true,
          )
        }
      >
        Resize map
      </button>
      {pins.map((p) => (
        <button key={p.id} onClick={p.onSelect}>
          {p.label}
        </button>
      ))}
    </div>
  ),
}));
vi.mock("./ScanForm", () => ({
  ScanForm: ({
    preselectedCampground,
  }: {
    preselectedCampground: { id: string; provider_id: number };
  }) => (
    <button>
      Monitor {preselectedCampground.provider_id}/{preselectedCampground.id}
    </button>
  ),
}));
const item = {
  id: "Camp/2/area/shared",
  provider_id: 2,
  provider_name: "Fixture",
  entity_type: "Campground",
  campground_id: "shared",
  campground_name: "Off page campground",
  recreation_area_id: "area",
  recreation_area_name: "Area",
  latitude: 35,
  longitude: -105,
};
const world = { west: -180, east: 180, south: -90, north: 90 };
beforeEach(() => {
  vi.mocked(hooks.useMapSummary).mockReturnValue({
    data: {
      total: 103,
      mappable_total: 102,
      unmappable_total: 1,
      bounds: world,
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof hooks.useMapSummary>);
  vi.mocked(hooks.useMapFeatures).mockReturnValue({
    data: {
      viewport: world,
      grid_level: 1,
      represented_total: 102,
      features: [
        { kind: "location", cell_id: "1:1:0", item },
        {
          kind: "group",
          cell_id: "1:0:0",
          count: 101,
          latitude: 0,
          longitude: -1,
          bounds: world,
        },
      ],
    },
    isFetching: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useMapFeatures>);
  vi.mocked(hooks.useMapMembers).mockReturnValue({
    data: { pages: [{ items: [item], total: 101, next_cursor: "next" }] },
    hasNextPage: true,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof hooks.useMapMembers>);
});
const open = () =>
  render(
    <MemoryRouter>
      <ExploreMap params={{}} saved={null} onSave={() => {}} />
    </MemoryRouter>,
  );
describe("Explore map discovery", () => {
  it("uses the initial regional extent instead of fitting the global catalog", () => {
    const bounds = { west: -106, east: -104, south: 34, north: 36 };
    render(
      <MemoryRouter>
        <ExploreMap
          params={{}}
          saved={null}
          onSave={() => {}}
          initialBounds={bounds}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("map-canvas")).toHaveAttribute(
      "data-bounds",
      JSON.stringify(bounds),
    );
  });
  it("debounces movement into list bounds without changing the map context", () => {
    vi.useFakeTimers();
    try {
      const onViewport = vi.fn();
      render(
        <MemoryRouter>
          <ExploreMap
            params={{ page: 3 }}
            saved={null}
            onSave={() => {}}
            onViewport={onViewport}
          />
        </MemoryRouter>,
      );
      fireEvent.click(screen.getByRole("button", { name: "Move map" }));
      fireEvent.click(screen.getByRole("button", { name: "Resize map" }));
      expect(onViewport).not.toHaveBeenCalled();
      act(() => {
        vi.advanceTimersByTime(150);
      });
      expect(onViewport).toHaveBeenCalledWith(
        { west: -106, east: -104, south: 34, north: 36 },
        true,
      );
    } finally {
      vi.useRealTimers();
    }
  });
  it("refreshes the list throughout continuous movement without waiting for a pause", () => {
    vi.useFakeTimers();
    try {
      const onViewport = vi.fn();
      render(
        <MemoryRouter>
          <ExploreMap
            params={{}}
            saved={null}
            onSave={() => {}}
            onViewport={onViewport}
          />
        </MemoryRouter>,
      );
      for (let index = 0; index < 5; index++) {
        fireEvent.click(screen.getByRole("button", { name: "Move map" }));
        act(() => {
          vi.advanceTimersByTime(100);
        });
      }
      expect(onViewport.mock.calls.length).toBeGreaterThanOrEqual(2);
    } finally {
      vi.useRealTimers();
    }
  });
  it("saves the latest camera immediately so collapsing cannot discard a recent pan", () => {
    const onSave = vi.fn();
    render(
      <MemoryRouter>
        <ExploreMap params={{}} saved={null} onSave={onSave} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Move map" }));
    expect(onSave).toHaveBeenCalledWith({
      context: "{}",
      moved: true,
      bounds: { west: -106, east: -104, south: 34, north: 36 },
      camera: { lat: 35, lng: -105, zoom: 9 },
    });
  });

  it.each([
    { params: {}, restores: true },
    { params: { query: "Changed" }, restores: false },
  ])(
    "restores a saved camera only for the same filter context ($restores)",
    ({ params, restores }) => {
      const camera = { lat: 35, lng: -105, zoom: 9 };
      render(
        <MemoryRouter>
          <ExploreMap
            params={params}
            saved={{ context: "{}", camera, bounds: world }}
            onSave={() => {}}
          />
        </MemoryRouter>,
      );
      if (restores)
        expect(screen.getByTestId("map-canvas")).toHaveAttribute(
          "data-camera",
          JSON.stringify(camera),
        );
      else
        expect(screen.getByTestId("map-canvas")).not.toHaveAttribute(
          "data-camera",
        );
    },
  );

  it("offers exact provider-qualified details and Monitor for an off-page place", () => {
    open();
    fireEvent.click(
      screen.getByRole("button", { name: "Off page campground" }),
    );
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute(
      "href",
      "/campground/2/shared",
    );
    expect(
      screen.getByRole("button", { name: "Monitor 2/shared" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/1 matching place.*cannot be mapped/),
    ).toBeInTheDocument();
  });
  it("keeps co-located members reachable through explicit bounded pages", () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "101 places" }));
    expect(
      screen.getByRole("heading", { name: "101 places in this group" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View places" }));
    expect(
      screen.getByRole("button", { name: "Load more" }),
    ).toBeInTheDocument();
    expect(hooks.useMapMembers).toHaveBeenLastCalledWith(
      {},
      { bounds: world, cellId: "1:0:0" },
    );
  });
  it("distinguishes failed summaries from empty results", () => {
    vi.mocked(hooks.useMapSummary).mockReturnValue({
      isError: true,
      isPending: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useMapSummary>);
    open();
    expect(
      screen.getByRole("button", { name: "Retry map summary" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("No places match your search."),
    ).not.toBeInTheDocument();
  });
  it("offers recreation-area details without a campground Monitor", () => {
    vi.mocked(hooks.useMapFeatures).mockReturnValue({
      data: {
        viewport: world,
        features: [
          {
            kind: "location",
            cell_id: "1:0:0",
            item: {
              ...item,
              id: "Area/2/area",
              entity_type: "RecreationArea",
              campground_id: null,
              campground_name: null,
            },
          },
        ],
      },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useMapFeatures>);
    open();
    fireEvent.click(screen.getByRole("button", { name: "Area" }));
    expect(screen.getByRole("link", { name: "Details" })).toHaveAttribute(
      "href",
      "/rec-area/2/area",
    );
    expect(
      screen.queryByRole("button", { name: /Monitor/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Selected map location")).toHaveFocus();
  });
  it("keeps data failure separate from a successful zero result", () => {
    vi.mocked(hooks.useMapFeatures).mockReturnValue({
      isError: true,
      isFetching: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof hooks.useMapFeatures>);
    open();
    expect(
      screen.getByRole("button", { name: "Retry map locations" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("No places match your search."),
    ).not.toBeInTheDocument();
  });
  it("filters out mapping results that have a lat/lon of 0/0", () => {
    vi.mocked(hooks.useMapFeatures).mockReturnValue({
      data: {
        viewport: world,
        grid_level: 1,
        represented_total: 1,
        features: [
          {
            kind: "location",
            cell_id: "1:0:0",
            item: {
              ...item,
              id: "Camp/2/area/zero",
              campground_name: "Zero Island",
              latitude: 0,
              longitude: 0,
            },
          },
        ],
      },
      isFetching: false,
      isError: false,
    } as unknown as ReturnType<typeof hooks.useMapFeatures>);
    open();
    expect(
      screen.queryByRole("button", { name: "Zero Island" }),
    ).not.toBeInTheDocument();
  });
});
