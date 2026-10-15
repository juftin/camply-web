import {
  render,
  screen,
  cleanup,
  fireEvent,
  act,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import type { MapOptions } from "maplibre-gl";
import { MapComponent } from "./MapComponent";

const sdk = vi.hoisted(() => {
  type Handler = (event: { sourceId?: string; error?: Error }) => void;
  class TestMap {
    center: { lng: number; lat: number };
    zoom: number;
    events = new Map<string, Set<Handler>>();
    constructor(public options: MapOptions) {
      const center = options.center as [number, number];
      this.center = { lng: center[0], lat: center[1] };
      this.zoom = options.zoom!;
    }
    on = vi.fn((name: string, handler: Handler) => {
      if (!this.events.has(name)) this.events.set(name, new Set());
      this.events.get(name)!.add(handler);
      return this;
    });
    off = vi.fn((name: string, handler: Handler) => {
      this.events.get(name)?.delete(handler);
      return this;
    });
    fire(name: string, event = {}) {
      this.events.get(name)?.forEach((handler) => handler(event));
    }
    getCenter = () => this.center;
    getZoom = () => this.zoom;
    getBounds = () => ({
      getWest: () => -180,
      getEast: () => 180,
      getSouth: () => -85.05112878,
      getNorth: () => 85.05112878,
    });
    jumpTo = vi.fn();
    fitBounds = vi.fn((bounds: [[number, number], [number, number]]) => {
      this.center = {
        lng: (bounds[0][0] + bounds[1][0]) / 2,
        lat: (bounds[0][1] + bounds[1][1]) / 2,
      };
      this.fire("moveend");
    });
    addControl = vi.fn();
    touchZoomRotate = { disableRotation: vi.fn() };
    resize = vi.fn();
    refreshTiles = vi.fn();
    remove = vi.fn();
  }
  class TestMarker {
    constructor(public options: { element: HTMLElement }) {}
    setLngLat = vi.fn((_point: [number, number]) => this);
    addTo = vi.fn((map: TestMap) => {
      (map.options.container as HTMLElement).appendChild(this.options.element);
      return this;
    });
    remove = vi.fn(() => this.options.element.remove());
  }
  const maps: TestMap[] = [];
  const markers: TestMarker[] = [];
  return {
    maps,
    markers,
    Map: vi.fn(function (options: MapOptions) {
      const map = new TestMap(options);
      maps.push(map);
      return map;
    }),
    Marker: vi.fn(function (options: { element: HTMLElement }) {
      const marker = new TestMarker(options);
      markers.push(marker);
      return marker;
    }),
    Popup: vi.fn(
      class {
        content!: HTMLElement;
        map?: TestMap;
        setDOMContent(content: HTMLElement) {
          this.content = content;
          return this;
        }
        setLngLat() {
          return this;
        }
        addTo(map: TestMap) {
          this.map = map;
          (map.options.container as HTMLElement).appendChild(this.content);
          return this;
        }
        remove() {
          this.content.remove();
          return this;
        }
      },
    ),
    setWorkerUrl: vi.fn(),
    NavigationControl: vi.fn(class {}),
    AttributionControl: vi.fn(class {}),
  };
});
vi.mock("maplibre-gl", () => sdk);
beforeEach(() => {
  sdk.maps.length = 0;
  sdk.markers.length = 0;
  vi.clearAllMocks();
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("MapLibre shared maps", () => {
  it("distinguishes initialization and resize from user navigation and group fitting", () => {
    const onMove = vi.fn();
    const bounds = { west: -2, east: 2, south: -2, north: 2 };
    const { rerender } = render(
      <MapComponent bounds={bounds} fitKey="search" onMove={onMove} />,
    );
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.anything(),
      true,
    );
    act(() => sdk.maps[0].fire("moveend"));
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.anything(),
      true,
    );
    act(() =>
      sdk.maps[0].fire("moveend", { originalEvent: new MouseEvent("mouseup") }),
    );
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.anything(),
      false,
    );
    rerender(<MapComponent bounds={bounds} fitKey="group" onMove={onMove} />);
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.anything(),
      false,
    );
  });
  it("reports camera changes during movement even when DOM event metadata is absent", () => {
    const onMove = vi.fn();
    render(
      <MapComponent
        bounds={{ west: -2, east: 2, south: -2, north: 2 }}
        fitKey="search"
        onMove={onMove}
      />,
    );
    const map = sdk.maps[0];
    onMove.mockClear();
    map.zoom += 1;
    act(() => map.fire("move"));
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({ zoom: map.zoom }),
      false,
    );
    onMove.mockClear();
    map.center = { lat: 1, lng: 1 };
    act(() => map.fire("moveend"));
    expect(onMove).toHaveBeenLastCalledWith(
      expect.anything(),
      expect.objectContaining({ lat: 1, lng: 1 }),
      false,
    );
  });
  it("shows safe place information on hover and focus and cleans up popups", () => {
    const onSelect = vi.fn();
    const { unmount } = render(
      <MapComponent
        pins={[
          {
            id: "hover",
            lat: 0,
            lng: 0,
            label: "<b>Camp name</b>",
            description: "Provider · Campground · CA",
            onSelect,
          },
        ]}
      />,
    );
    const marker = screen.getByRole("button", { name: "<b>Camp name</b>" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.mouseEnter(marker);
    expect(screen.getByRole("tooltip")).toHaveTextContent("<b>Camp name</b>");
    expect(screen.getByRole("tooltip").querySelector("b")).toBeNull();
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Provider · Campground · CA",
    );
    expect(onSelect).not.toHaveBeenCalled();
    fireEvent.mouseLeave(marker);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.focus(marker);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    fireEvent.keyDown(marker, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.blur(marker);
    fireEvent.focus(marker);
    fireEvent.blur(marker);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.mouseEnter(marker);
    unmount();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    fireEvent.mouseEnter(marker);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
  it("renders valid zero locations with a keyless raster style and safe attribution/requests", () => {
    render(
      <MapComponent
        latitude={0}
        longitude={0}
        label="Primary"
        additionalLocations={[
          { lat: 1, lng: 2, label: "Related", type: "campground" },
        ]}
      />,
    );
    expect(screen.getByLabelText("Primary")).toBeInTheDocument();
    expect(screen.getByLabelText("Related")).toBeInTheDocument();
    const map = sdk.maps[0];
    expect(map.options.style).toMatchObject({
      version: 8,
      sources: {
        basemap: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          maxzoom: 19,
          attribution: expect.stringContaining(
            'href="https://www.openstreetmap.org/copyright"',
          ),
        },
      },
    });
    expect(
      map.options.transformRequest!(
        "https://example.test/tiles.png",
        undefined,
      ),
    ).toEqual({
      url: "https://example.test/tiles.png",
      credentials: "same-origin",
      referrerPolicy: "strict-origin",
    });
    expect(sdk.AttributionControl).toHaveBeenCalledWith({ compact: false });
    expect(map.fitBounds).toHaveBeenCalledWith(
      [
        [0, 0],
        [2, 1],
      ],
      expect.objectContaining({ maxZoom: 12, animate: false }),
    );
  });
  it("reports loading until the renderer is ready and recovers a lost graphics context", () => {
    render(<MapComponent latitude={0} longitude={0} />);
    expect(screen.getByText("Loading map…")).toBeInTheDocument();
    act(() => sdk.maps[0].fire("load"));
    expect(screen.queryByText("Loading map…")).not.toBeInTheDocument();
    sdk.maps[0].center = { lng: -105, lat: 35 };
    sdk.maps[0].zoom = 9;
    act(() => sdk.maps[0].fire("moveend"));
    act(() => sdk.maps[0].fire("webglcontextlost"));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "graphics context was lost",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry map" }));
    expect(sdk.maps[0].remove).toHaveBeenCalledOnce();
    expect(sdk.maps[1].options).toMatchObject({ center: [-105, 35], zoom: 9 });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Loading map…")).toBeInTheDocument();
  });
  it("handles StrictMode remounts and container resizing without refitting or leaking observers", () => {
    const callbacks: ResizeObserverCallback[] = [];
    const disconnect = vi.fn();
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: ResizeObserverCallback) {
          callbacks.push(callback);
        }
        observe() {}
        disconnect = disconnect;
      },
    );
    const { unmount } = render(
      <StrictMode>
        <MapComponent latitude={0} longitude={0} />
      </StrictMode>,
    );
    expect(sdk.maps).toHaveLength(2);
    expect(sdk.maps[0].remove).toHaveBeenCalledOnce();
    const current = sdk.maps[1];
    current.jumpTo.mockClear();
    act(() => callbacks[1]([], {} as ResizeObserver));
    expect(current.resize).toHaveBeenCalledOnce();
    expect(current.jumpTo).not.toHaveBeenCalled();
    unmount();
    expect(current.remove).toHaveBeenCalledOnce();
    expect(disconnect).toHaveBeenCalledTimes(2);
  });

  it("keeps a single point at a useful zoom and skips invalid markers", () => {
    render(
      <MapComponent
        latitude={0}
        longitude={0}
        additionalLocations={[{ lat: 91, lng: 0 }]}
      />,
    );
    expect(sdk.markers).toHaveLength(1);
    expect(sdk.maps[0].jumpTo).toHaveBeenCalledWith({
      center: [0, 0],
      zoom: 12,
    });
  });
  it("updates markers without recreating the map or refitting the same Explore context", () => {
    const { rerender, unmount } = render(
      <MapComponent latitude={0} longitude={0} fitKey="same-filters" />,
    );
    const map = sdk.maps[0];
    const original = sdk.markers[0];
    map.jumpTo.mockClear();
    rerender(
      <MapComponent
        latitude={1}
        longitude={1}
        label="Next"
        fitKey="same-filters"
      />,
    );
    expect(sdk.Map).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("Next")).toBeInTheDocument();
    expect(map.jumpTo).not.toHaveBeenCalled();
    expect(original.remove).toHaveBeenCalled();
    unmount();
    expect(map.remove).toHaveBeenCalledOnce();
  });
  it("restores a saved camera without resetting it to global bounds", () => {
    const onMove = vi.fn();
    render(
      <MapComponent
        camera={{ lat: 35, lng: -105, zoom: 9 }}
        bounds={{ west: -180, east: 180, south: -90, north: 90 }}
        fitKey="filters"
        onMove={onMove}
      />,
    );
    const map = sdk.maps[0];
    expect(map.options).toMatchObject({ center: [-105, 35], zoom: 9 });
    expect(map.fitBounds).not.toHaveBeenCalled();
    expect(onMove).toHaveBeenCalledWith(
      expect.anything(),
      {
        lat: 35,
        lng: -105,
        zoom: 9,
      },
      true,
    );
  });
  it("ignores late movement after collapse removes the map", () => {
    const onMove = vi.fn();
    const { unmount } = render(
      <MapComponent latitude={0} longitude={0} onMove={onMove} />,
    );
    const map = sdk.maps[0];
    unmount();
    onMove.mockClear();
    expect(() => map.fire("moveend")).not.toThrow();
    expect(onMove).not.toHaveBeenCalled();
  });
  it("keeps dateline neighbors in the same world after fitting", () => {
    render(
      <MapComponent
        latitude={1}
        longitude={179}
        additionalLocations={[{ lat: 2, lng: -179, label: "Neighbor" }]}
      />,
    );
    expect(sdk.maps[0].fitBounds).toHaveBeenCalledWith(
      [
        [179, 1],
        [181, 2],
      ],
      expect.anything(),
    );
    expect(
      sdk.markers.some((marker) =>
        marker.setLngLat.mock.calls.some((call) => call[0][0] === 181),
      ),
    ).toBe(true);
  });
  it("keeps tile failures local and retries ordinary cached tile URLs", () => {
    render(<MapComponent latitude={0} longitude={0} />);
    const map = sdk.maps[0];
    act(() =>
      map.fire("error", {
        sourceId: "basemap",
        error: new Error("Unavailable"),
      }),
    );
    expect(
      screen.getByText(/Basemap tiles could not load/),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry tiles" }));
    expect(map.refreshTiles).toHaveBeenCalledWith("basemap");
    expect(
      screen.queryByText(/Basemap tiles could not load/),
    ).not.toBeInTheDocument();
    expect(
      map.options.transformRequest!("https://example.test/tile.png", undefined),
    ).not.toHaveProperty("cache");
  });
  it("provides named buttons that activate selections by click, Enter and Space", () => {
    const onSelect = vi.fn();
    render(
      <MapComponent
        pins={[
          {
            id: "qualified",
            lat: 0,
            lng: 0,
            label: "Keyboard place",
            onSelect,
          },
        ]}
      />,
    );
    const marker = screen.getByRole("button", { name: "Keyboard place" });
    fireEvent.click(marker);
    fireEvent.keyDown(marker, { key: "Enter" });
    fireEvent.keyDown(marker, { key: " " });
    expect(onSelect).toHaveBeenCalledTimes(3);
  });
  it("keeps invalid settings and unavailable WebGL recoverable within the map", () => {
    vi.stubEnv("VITE_MAP_TILE_URL", "javascript:bad");
    const { unmount } = render(<MapComponent latitude={0} longitude={0} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/attribution|XYZ/i);
    expect(sdk.Map).not.toHaveBeenCalled();
    unmount();
    vi.unstubAllEnvs();
    sdk.Map.mockImplementationOnce(() => {
      throw new Error("WebGL is unavailable");
    });
    render(<MapComponent latitude={0} longitude={0} />);
    expect(screen.getByRole("alert")).toHaveTextContent("WebGL is unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry map" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
