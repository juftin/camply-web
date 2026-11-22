import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ScanDetailResponse } from "@/lib/structs";
import { CoverageSummary } from "./CoverageSummary";

const areaScan: ScanDetailResponse = {
  id: "area-scan-1",
  provider_id: 1,
  destination_type: "recreation_area",
  destination_name: "Synthetic Basin",
  campground_id: null,
  campground_name: null,
  recreation_area_id: "area-1",
  recreation_area_name: "Synthetic Basin",
  coverage_mode: "selected",
  eligible_campground_count: 2,
  unavailable_selection_count: 1,
  checked_campground_count: 1,
  pending_campground_count: 0,
  failed_campground_count: 1,
  coverage_status: "partial",
  start_date: "2027-07-01",
  end_date: "2027-07-10",
  is_active: true,
  min_stay_length: 2,
  preferred_types: [],
  require_electric: false,
  found_count: 1,
  last_checked_at: "2027-01-01T12:00:00Z",
  created_at: "2027-01-01T00:00:00Z",
  campgrounds: [
    {
      provider_id: 1,
      campground_id: "cg-a",
      campground_name: "North Pine",
      eligible: true,
      outcome: "success",
      last_checked_at: "2027-01-01T11:55:00Z",
    },
    {
      provider_id: 1,
      campground_id: "cg-b",
      campground_name: "Failed Ridge",
      eligible: true,
      outcome: "failed",
      last_checked_at: "2027-01-01T10:00:00Z",
    },
    {
      provider_id: 1,
      campground_id: "cg-c",
      campground_name: "Closed Creek",
      eligible: false,
      outcome: "failed",
      unavailable_reason:
        "Campground is no longer eligible in this recreation area",
    },
  ],
  results: [],
};

describe("CoverageSummary", () => {
  it("renders structured counts, partial warning, and expandable member list with relative timestamps", async () => {
    const user = userEvent.setup();
    render(<CoverageSummary scan={areaScan} />);

    const section = screen.getByRole("region", { name: "Campground coverage" });
    expect(
      within(section).getByText("Selected campgrounds"),
    ).toBeInTheDocument();
    expect(within(section).getByText("2 eligible")).toBeInTheDocument();
    expect(within(section).getByText("1 checked")).toBeInTheDocument();
    expect(within(section).getByText("1 failed")).toBeInTheDocument();
    expect(within(section).getByText("1 unavailable")).toBeInTheDocument();
    expect(
      within(section).getByText(
        /Results may be incomplete; some campgrounds are unchecked or failed/i,
      ),
    ).toBeInTheDocument();

    // Expand per-campground breakdown
    await user.click(within(section).getByText(/Campground status details/i));
    expect(within(section).getByText("North Pine")).toBeInTheDocument();
    expect(within(section).getByText("Failed Ridge")).toBeInTheDocument();
    expect(within(section).getByText("Closed Creek")).toBeInTheDocument();
    expect(
      within(section).getByText(
        "Campground is no longer eligible in this recreation area",
      ),
    ).toBeInTheDocument();

    // Never expose raw ISO timestamp strings
    expect(
      within(section).queryByText(/2027-01-01T11:55:00Z/),
    ).not.toBeInTheDocument();
    expect(
      within(section).queryByText(/2027-01-01T10:00:00Z/),
    ).not.toBeInTheDocument();
  });
});
