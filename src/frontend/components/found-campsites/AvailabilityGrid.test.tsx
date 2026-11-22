import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { filterAndSortSites, normalizeFoundSites } from "@/lib/availability";
import { AvailabilityGrid } from "./AvailabilityGrid";

const rawResults = [
  {
    provider_id: 1,
    campground_id: "cg-1",
    campground_name: "North Pines",
    campsite_id: "10",
    campsite_name: "Site 010",
    campsite_type: "RV",
    is_electric: true,
    is_accessible: true,
    max_vehicle_length: 35,
    permitted_equipment: ["RV", "Trailer"],
    available_dates: ["2027-07-01", "2027-07-02", "2027-07-03"],
    booking_url: "https://book.example/north-10",
    is_stale: true,
  },
  {
    provider_id: 1,
    campground_id: "cg-2",
    campground_name: "Lower Pines",
    campsite_id: "11",
    campsite_name: "Site 011",
    campsite_type: "TENT",
    is_electric: false,
    is_accessible: false,
    available_dates: ["2027-07-04", "2027-07-05"],
    booking_url: "https://book.example/lower-11",
    is_stale: false,
  },
];

describe("AvailabilityGrid", () => {
  it("renders campsites as rows and dates as columns, navigates windows, and inspects stays on cell click", async () => {
    const user = userEvent.setup();
    const sites = normalizeFoundSites(rawResults, 2);
    const items = filterAndSortSites(sites, "", null, "soonest", true);
    const onWindowStartChange = vi.fn();

    render(
      <AvailabilityGrid
        scanStartDate="2027-07-01"
        scanEndDate="2027-07-25"
        items={items}
        totalMatchingSites={items.length}
        page={0}
        pageCount={1}
        onPageChange={vi.fn()}
        isMultiCampground={true}
        dateSelection={null}
        windowStartDate="2027-07-01"
        onWindowStartChange={onWindowStartChange}
        includeYearByDefault={false}
      />,
    );

    expect(screen.getByText("Site 010")).toBeInTheDocument();
    expect(screen.getByText("North Pines")).toBeInTheDocument();
    expect(screen.getByText("Site 011")).toBeInTheDocument();
    expect(screen.getByText("Lower Pines")).toBeInTheDocument();

    // Window navigation
    expect(
      screen.getByRole("button", { name: "Previous dates" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Next dates" }));
    expect(onWindowStartChange).toHaveBeenCalledWith("2027-07-15");

    // Click an available cell to inspect the stay
    const cell = screen.getByRole("button", {
      name: /Site 010.*Jul 1, 2027/i,
    });
    expect(cell).toHaveAttribute("aria-pressed", "false");
    await user.click(cell);
    expect(cell).toHaveAttribute("aria-pressed", "true");

    const inspector = screen.getByRole("region", {
      name: "Selected stay details",
    });
    expect(inspector).toHaveTextContent("3 nights");
    expect(inspector).toHaveTextContent("Electric hookup");
    expect(inspector).toHaveTextContent("Up to 35 ft");
    expect(inspector).toHaveTextContent(/Stale/i);
    expect(
      screen.getByRole("link", {
        name: "View Site 010 on provider website (North Pines)",
      }),
    ).toHaveAttribute("href", "https://book.example/north-10");

    // Dismiss via Escape
    await user.keyboard("{Escape}");
    expect(
      screen.queryByRole("region", { name: "Selected stay details" }),
    ).not.toBeInTheDocument();
  });

  it("clears inspected stay automatically when the inspected site disappears", async () => {
    const user = userEvent.setup();
    const sites = normalizeFoundSites(rawResults, 2);
    const items = filterAndSortSites(sites, "", null, "soonest", true);

    const { rerender } = render(
      <AvailabilityGrid
        scanStartDate="2027-07-01"
        scanEndDate="2027-07-10"
        items={items}
        totalMatchingSites={items.length}
        page={0}
        pageCount={1}
        onPageChange={vi.fn()}
        isMultiCampground={true}
        dateSelection={null}
        windowStartDate="2027-07-01"
        onWindowStartChange={vi.fn()}
        includeYearByDefault={false}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: /Site 010.*Jul 1, 2027/i }),
    );
    expect(
      screen.getByRole("region", { name: "Selected stay details" }),
    ).toBeInTheDocument();

    rerender(
      <AvailabilityGrid
        scanStartDate="2027-07-01"
        scanEndDate="2027-07-10"
        items={[items[1]]}
        totalMatchingSites={1}
        page={0}
        pageCount={1}
        onPageChange={vi.fn()}
        isMultiCampground={true}
        dateSelection={null}
        windowStartDate="2027-07-01"
        onWindowStartChange={vi.fn()}
        includeYearByDefault={false}
      />,
    );

    expect(
      screen.queryByRole("region", { name: "Selected stay details" }),
    ).not.toBeInTheDocument();
  });
});
