import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { FoundCampsites } from "./FoundCampsites";
import type { ScanDetailResponse } from "@/lib/structs";

const baseScan: ScanDetailResponse = {
  id: "scan-1",
  provider_id: 1,
  campground_id: "cg-1",
  campground_name: "Yosemite Pines",
  recreation_area_name: "Yosemite",
  start_date: "2027-07-01",
  end_date: "2027-07-05",
  is_active: true,
  min_stay_length: 1,
  preferred_types: [],
  require_electric: false,
  require_accessible: false,
  min_rv_length: null,
  found_count: 1,
  last_checked_at: "2027-01-01T12:00:00Z",
  created_at: "2027-01-01T00:00:00Z",
  results: [
    {
      provider_id: 1,
      campground_id: "cg-1",
      campground_name: "Yosemite Pines",
      campsite_id: "10",
      campsite_name: "Loop A Site 10",
      campsite_type: "RV",
      is_electric: true,
      is_accessible: true,
      max_vehicle_length: 35,
      permitted_equipment: ["RV", "Trailer"],
      available_dates: ["2027-07-01"],
      booking_url: "https://book.example/site/10",
    },
  ],
};

describe("FoundCampsites capability display", () => {
  it("renders persisted vehicle length, permitted equipment, electric hookup, and ADA labels", () => {
    render(
      <MemoryRouter>
        <FoundCampsites scan={baseScan} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Up to 35 ft")).toBeInTheDocument();
    expect(screen.getByText("RV, Trailer")).toBeInTheDocument();
    expect(screen.getByText("Electric hookup")).toBeInTheDocument();
    expect(screen.getByText("Accessible")).toBeInTheDocument();
  });
});
