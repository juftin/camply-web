import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { RecreationArea } from "./RecreationArea";
import { destinationDetails } from "@/test/destination-details";

// Layout and dragging are exercised with the real Embla engine in browser snapshots.
vi.mock("embla-carousel-react", () => ({
  default: () => [() => {}, undefined],
}));
vi.mock("@/lib/api", () => ({
  getCampground: vi.fn(),
  getProvider: vi.fn(),
  getRecreationArea: vi.fn(),
  getCampgrounds: vi.fn(),
}));
vi.mock("@/components/SearchBar", () => ({ SearchBar: () => null }));
vi.mock("@/components/ScanForm", () => ({ ScanForm: () => null }));
vi.mock("@/components/MapComponent", () => ({
  MapComponent: ({
    latitude,
    longitude,
    additionalLocations,
  }: {
    latitude: number;
    longitude: number;
    additionalLocations: { lat: number; lng: number }[];
  }) => (
    <div data-testid="map">
      {latitude}/{longitude}/{additionalLocations.length}
      <span data-testid="related-coordinates">
        {additionalLocations.map((p) => `${p.lat}/${p.lng}`).join(",")}
      </span>
    </div>
  ),
}));
const campground = {
  id: "zero",
  provider_id: 2,
  recreation_area_id: "area",
  name: "Synthetic zero",
  description: null,
  state: null,
  country: null,
  latitude: 37,
  longitude: -119,
  enabled: true,
  reservable: true,
  url: "",
};
const area = { ...campground, id: "area", name: "Synthetic area" };
function open() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/rec-area/2/area"]}>
        <Routes>
          <Route
            path="/rec-area/:providerId/:recreationAreaId"
            element={<RecreationArea />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
describe("RecreationArea location coordinates", () => {
  it("shows area enrichment and preserves the campground list", async () => {
    vi.mocked(api.getProvider).mockResolvedValue({
      id: 2,
      name: "Fixture",
      description: null,
      url: "",
      enabled: true,
    });
    vi.mocked(api.getRecreationArea).mockResolvedValue({
      ...area,
      details: destinationDetails(),
    });
    vi.mocked(api.getCampgrounds).mockResolvedValue([campground]);
    open();
    expect(
      await screen.findByRole("button", {
        name: "View Synthetic area photo 1",
      }),
    ).toBeVisible();
    expect(screen.getByText("Synthetic zero")).toBeVisible();
    expect(screen.getByText("Follow the signed road.")).toBeVisible();
    const map = screen.getByTestId("map");
    const information = screen.getByRole("heading", {
      name: "Know before you go",
    });
    expect(
      map.compareDocumentPosition(information) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      screen
        .getByRole("heading", { name: "Photos" })
        .compareDocumentPosition(map) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it.each([
    { latitude: 0, longitude: 10 },
    { latitude: 10, longitude: 0 },
  ])(
    "renders valid coordinates $latitude/$longitude and gives missing campground locations the area coordinates",
    async (coordinates) => {
      vi.mocked(api.getProvider).mockResolvedValue({
        id: 2,
        name: "Fixture",
        description: null,
        url: "",
        enabled: true,
      });
      vi.mocked(api.getCampground).mockResolvedValue(campground);
      vi.mocked(api.getRecreationArea).mockResolvedValue({
        ...area,
        ...coordinates,
      });
      vi.mocked(api.getCampgrounds).mockResolvedValue([
        { ...campground, id: "placeholder", latitude: 0, longitude: 0 },
        { ...campground, id: "equator", latitude: 0, longitude: 10 },
        { ...campground, id: "meridian", latitude: 10, longitude: 0 },
        { ...campground, id: "missing", latitude: null },
      ]);
      open();
      expect(await screen.findByTestId("map")).toHaveTextContent(
        `${coordinates.latitude}/${coordinates.longitude}/4`,
      );
      expect(screen.getByTestId("related-coordinates")).toHaveTextContent(
        `${coordinates.latitude}/${coordinates.longitude},0/10,10/0,${coordinates.latitude}/${coordinates.longitude}`,
      );
    },
  );
  it.each([
    { latitude: 0, longitude: 0 },
    { latitude: null, longitude: -119 },
  ])(
    "keeps detail content without a map for primary coordinates $latitude/$longitude",
    async (coordinates) => {
      vi.mocked(api.getProvider).mockResolvedValue({
        id: 2,
        name: "Fixture",
        description: null,
        url: "",
        enabled: true,
      });
      vi.mocked(api.getCampground).mockResolvedValue(campground);
      vi.mocked(api.getRecreationArea).mockResolvedValue({
        ...area,
        ...coordinates,
      });
      vi.mocked(api.getCampgrounds).mockResolvedValue([]);
      open();
      await screen.findByRole("heading", { name: "Synthetic area" });
      expect(screen.queryByTestId("map")).not.toBeInTheDocument();
    },
  );
});
