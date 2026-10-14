import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { Campground } from "./Campground";
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
    additionalLocations: unknown[];
  }) => (
    <div data-testid="map">
      {latitude}/{longitude}/{additionalLocations.length}
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
  latitude: 0,
  longitude: 0,
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
  it("renders zero primary and related coordinates", async () => {
    vi.mocked(api.getProvider).mockResolvedValue({
      id: 2,
      name: "Fixture",
      description: null,
      url: "",
      enabled: true,
    });
    vi.mocked(api.getCampground).mockResolvedValue(campground);
    vi.mocked(api.getRecreationArea).mockResolvedValue(area);
    vi.mocked(api.getCampgrounds).mockResolvedValue([
      { ...campground, id: "related" },
    ]);
    open();
    expect(await screen.findByTestId("map")).toHaveTextContent("0/0/1");
  });
  it("keeps detail content when primary coordinates are missing", async () => {
    vi.mocked(api.getProvider).mockResolvedValue({
      id: 2,
      name: "Fixture",
      description: null,
      url: "",
      enabled: true,
    });
    vi.mocked(api.getCampground).mockResolvedValue({
      ...campground,
      latitude: null,
    });
    vi.mocked(api.getRecreationArea).mockResolvedValue({
      ...area,
      latitude: null,
    });
    vi.mocked(api.getCampgrounds).mockResolvedValue([]);
    open();
    await screen.findByRole("heading", { name: "Synthetic zero" });
    expect(screen.queryByTestId("map")).not.toBeInTheDocument();
  });
});
