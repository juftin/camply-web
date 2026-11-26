import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { Campground } from "./Campground";
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
      <MemoryRouter initialEntries={["/campground/2/zero"]}>
        <Routes>
          <Route
            path="/campground/:providerId/:campgroundId"
            element={<Campground />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
describe("Campground location coordinates", () => {
  it("shows its own enrichment without borrowing recreation-area photos", async () => {
    vi.mocked(api.getProvider).mockResolvedValue({
      id: 2,
      name: "Fixture",
      description: null,
      url: "",
      enabled: true,
    });
    vi.mocked(api.getCampground).mockResolvedValue({
      ...campground,
      details: destinationDetails({
        description: "A richer campground description.",
      }),
    });
    vi.mocked(api.getRecreationArea).mockResolvedValue({
      ...area,
      details: destinationDetails({
        photos: [
          {
            url: "https://images.example.test/parent.jpg",
            caption: "Parent-only photo",
            is_primary: true,
          },
        ],
      }),
    });
    vi.mocked(api.getCampgrounds).mockResolvedValue([]);
    open();
    expect(
      await screen.findByRole("button", {
        name: "View Synthetic zero photo 1",
      }),
    ).toBeVisible();
    expect(screen.getByText("A richer campground description.")).toBeVisible();
    expect(screen.queryByAltText("Parent-only photo")).toBeNull();
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

  it("keeps an unenriched campground free of its parent's gallery", async () => {
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
      details: destinationDetails(),
    });
    vi.mocked(api.getCampgrounds).mockResolvedValue([]);
    open();
    await screen.findByRole("heading", { name: "Synthetic zero" });
    expect(screen.queryByRole("heading", { name: "Photos" })).toBeNull();
  });

  it.each([
    { latitude: 0, longitude: 10 },
    { latitude: 10, longitude: 0 },
  ])(
    "preserves valid coordinates $latitude/$longitude and inherits parent coordinates for related pins",
    async (coordinates) => {
      vi.mocked(api.getProvider).mockResolvedValue({
        id: 2,
        name: "Fixture",
        description: null,
        url: "",
        enabled: true,
      });
      vi.mocked(api.getCampground).mockResolvedValue({
        ...campground,
        ...coordinates,
      });
      vi.mocked(api.getRecreationArea).mockResolvedValue(area);
      vi.mocked(api.getCampgrounds).mockResolvedValue([
        { ...campground, id: "placeholder", latitude: 0, longitude: 0 },
        { ...campground, id: "equator", latitude: 0, longitude: 10 },
        { ...campground, id: "meridian", latitude: 10, longitude: 0 },
        { ...campground, id: "missing", latitude: null },
        campground,
      ]);
      open();
      expect(await screen.findByTestId("map")).toHaveTextContent(
        `${coordinates.latitude}/${coordinates.longitude}/4`,
      );
      expect(screen.getByTestId("related-coordinates")).toHaveTextContent(
        "37/-119,0/10,10/0,37/-119",
      );
    },
  );
  it.each([
    { latitude: 0, longitude: 0 },
    { latitude: null, longitude: -118 },
    { latitude: 38, longitude: null },
    { latitude: null, longitude: null },
    { latitude: 91, longitude: 10 },
  ])(
    "inherits its parent's complete coordinate pair for $latitude/$longitude",
    async (coordinates) => {
      vi.mocked(api.getProvider).mockResolvedValue({
        id: 2,
        name: "Fixture",
        description: null,
        url: "",
        enabled: true,
      });
      vi.mocked(api.getCampground).mockResolvedValue({
        ...campground,
        ...coordinates,
      });
      vi.mocked(api.getRecreationArea).mockResolvedValue(area);
      vi.mocked(api.getCampgrounds).mockResolvedValue([]);
      open();
      expect(await screen.findByTestId("map")).toHaveTextContent("37/-119/0");
    },
  );
  it.each([
    { latitude: 0, longitude: 0 },
    { latitude: null, longitude: -119 },
    { latitude: null, longitude: null, recreation_area_id: null },
  ])(
    "keeps detail content without a map when neither campground nor parent has usable coordinates $latitude/$longitude",
    async (coordinates) => {
      vi.mocked(api.getProvider).mockResolvedValue({
        id: 2,
        name: "Fixture",
        description: null,
        url: "",
        enabled: true,
      });
      vi.mocked(api.getCampground).mockResolvedValue({
        ...campground,
        ...coordinates,
      });
      vi.mocked(api.getRecreationArea).mockResolvedValue({
        ...area,
        ...coordinates,
      });
      vi.mocked(api.getCampgrounds).mockResolvedValue([]);
      open();
      expect(
        await screen.findByRole("heading", { name: "Synthetic zero" }),
      ).toHaveClass("break-words");
      expect(screen.queryByTestId("map")).not.toBeInTheDocument();
    },
  );
});
