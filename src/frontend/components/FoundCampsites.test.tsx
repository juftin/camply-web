import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  end_date: "2027-07-20",
  is_active: true,
  min_stay_length: 2,
  preferred_types: [],
  require_electric: false,
  require_accessible: false,
  min_rv_length: null,
  found_count: 3,
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
      available_dates: ["2027-07-01", "2027-07-02", "2027-07-08", "2027-07-09"],
      booking_url: "https://book.example/site/10",
    },
    {
      provider_id: 1,
      campground_id: "cg-1",
      campground_name: "Yosemite Pines",
      campsite_id: "11",
      campsite_name: "Loop B Site 11",
      campsite_type: "TENT",
      is_electric: false,
      is_accessible: false,
      available_dates: ["2027-07-01", "2027-07-02", "2027-07-03", "2027-07-04"],
      booking_url: "https://book.example/site/11",
    },
    {
      provider_id: 1,
      campground_id: "cg-1",
      campground_name: "Yosemite Pines",
      campsite_id: "12",
      campsite_name: "",
      campsite_type: null,
      is_electric: null,
      is_accessible: null,
      available_dates: ["2027-07-02", "2027-07-03"],
      booking_url: "",
    },
  ],
};

function renderFound(scan: ScanDetailResponse = baseScan) {
  return render(
    <MemoryRouter>
      <FoundCampsites scan={scan} />
    </MemoryRouter>,
  );
}

describe("FoundCampsites", () => {
  it("renders deduplicated campsite cards with capabilities, fallback names, and a single disclaimer", () => {
    renderFound();

    // Loop A Site 10 has 2 stays but renders once as a deduplicated card
    expect(screen.getAllByText("Loop A Site 10")).toHaveLength(1);
    expect(screen.getByText("Campsite 12")).toBeInTheDocument();
    expect(screen.getByText("Up to 35 ft")).toBeInTheDocument();
    expect(screen.getByText("RV, Trailer")).toBeInTheDocument();
    expect(screen.getByText("Electric hookup")).toBeInTheDocument();
    expect(screen.getByText("Accessible")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "3 sites · 4 openings",
    );

    // Only one provider booking disclaimer
    expect(screen.getAllByText(/confirm stay rules/i)).toHaveLength(1);
  });

  it("filters overlapping openings via single-night and check-in/check-out calendar clicks and highlights matching stays", async () => {
    const user = userEvent.setup();
    renderFound();

    const calendar = screen.getByRole("region", {
      name: "Availability calendar",
    });

    // Click Jul 2: all 3 sites cover night of Jul 2
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 2, 2027 — 3 sites available/i,
      }),
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "3 sites · 3 openings",
    );

    // Click Jul 4 as check-out (range Jul 2 -> Jul 4, 2 nights: Jul 2 & Jul 3)
    // Site 10 ends Jul 3 -> excluded; Site 11 (Jul 1-5) and Campsite 12 (Jul 2-4) match!
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 4, 2027/i,
      }),
    );
    expect(screen.queryByText("Loop A Site 10")).not.toBeInTheDocument();
    expect(screen.getByText("Loop B Site 11")).toBeInTheDocument();
    expect(screen.getByText("Campsite 12")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "2 sites · 2 openings",
    );

    // Clear dates restores all 3 sites
    await user.click(
      within(calendar).getByRole("button", { name: "Clear dates" }),
    );
    expect(screen.getByText("Loop A Site 10")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "3 sites · 4 openings",
    );
  });

  it("caps stay chips at 4 per card with inline expansion", async () => {
    const user = userEvent.setup();
    renderFound({
      ...baseScan,
      min_stay_length: 1,
      results: [
        {
          ...baseScan.results[0],
          available_dates: [
            "2027-07-01",
            "2027-07-03",
            "2027-07-05",
            "2027-07-07",
            "2027-07-09",
            "2027-07-11",
          ],
        },
      ],
    });

    expect(
      screen.getByRole("button", { name: /\+2 more stays/i }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /\+2 more stays/i }));
    expect(
      screen.getByRole("button", { name: /Show fewer stays/i }),
    ).toBeInTheDocument();
  });

  it("supports full-result search, sort modes, pagination at 10 sites, and filter-empty reset", async () => {
    const user = userEvent.setup();
    const manyScan: ScanDetailResponse = {
      ...baseScan,
      found_count: 12,
      results: Array.from({ length: 12 }, (_, idx) => ({
        ...baseScan.results[0],
        campsite_id: `s-${idx + 1}`,
        campsite_name: `Synthetic site ${idx + 1}`,
        available_dates: ["2027-07-01", "2027-07-02"],
      })),
    };
    renderFound(manyScan);

    expect(
      screen.getAllByRole("link", { name: /View Synthetic site/i }),
    ).toHaveLength(10);
    expect(screen.getByText("1–10 of 12 sites")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next campsites" }));
    expect(
      screen.getAllByRole("link", { name: /View Synthetic site/i }),
    ).toHaveLength(2);
    expect(screen.getByText("11–12 of 12 sites")).toBeInTheDocument();

    // Search resets to page 1 across all sites
    await user.type(
      screen.getByRole("searchbox", { name: "Search found campsites" }),
      "site 12",
    );
    expect(screen.getByText("Synthetic site 12")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("1 site · 1 opening");

    // Empty search reset
    await user.clear(
      screen.getByRole("searchbox", { name: "Search found campsites" }),
    );
    await user.type(
      screen.getByRole("searchbox", { name: "Search found campsites" }),
      "missing",
    );
    expect(
      screen.getByText("No campsites match your search."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getByText("1–10 of 12 sites")).toBeInTheDocument();

    // Sort selector exposes all 4 modes
    const sortSelect = screen.getByRole("combobox", { name: "Sort campsites" });
    await user.selectOptions(sortSelect, "longest");
    await user.selectOptions(sortSelect, "most_nights");
    await user.selectOptions(sortSelect, "name");
    await user.selectOptions(sortSelect, "soonest");
  });

  it("switches cleanly between Cards and Grid views while preserving search, sort, and active dates", async () => {
    const user = userEvent.setup();
    renderFound();

    const calendar = screen.getByRole("region", {
      name: "Availability calendar",
    });
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 2, 2027 — 3 sites available/i,
      }),
    );
    await user.type(
      screen.getByRole("searchbox", { name: "Search found campsites" }),
      "Loop",
    );

    const viewGroup = screen.getByRole("group", { name: "Results view" });
    const gridBtn = within(viewGroup).getByRole("button", { name: "Grid" });
    const cardsBtn = within(viewGroup).getByRole("button", { name: "Cards" });

    expect(cardsBtn).toHaveAttribute("aria-pressed", "true");
    await user.click(gridBtn);
    expect(gridBtn).toHaveAttribute("aria-pressed", "true");

    // Search + date filter stay active in Grid view
    expect(screen.getByText("Loop A Site 10")).toBeInTheDocument();
    expect(screen.getByText("Loop B Site 11")).toBeInTheDocument();
    expect(screen.queryByText("Campsite 12")).not.toBeInTheDocument();
    expect(screen.getByText(/Filtered dates:/i)).toBeInTheDocument();

    // Inspect an available cell in Grid view
    await user.click(
      screen.getByRole("button", { name: /Loop A Site 10.*Jul 2, 2027/i }),
    );
    expect(
      screen.getByRole("region", { name: "Selected stay details" }),
    ).toBeInTheDocument();

    // Switch back to Cards view — filters still intact
    await user.click(cardsBtn);
    expect(cardsBtn).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("status")).toHaveTextContent(
      "2 sites · 2 openings",
    );
  });

  it("shows distinct date-filter-only and combined search+date empty states with one-click reset", async () => {
    const user = userEvent.setup();
    renderFound();

    const calendar = screen.getByRole("region", {
      name: "Availability calendar",
    });

    // Click an in-window date with no openings (Jul 15)
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 15, 2027 — no openings/i,
      }),
    );
    expect(
      screen.getByText(
        "No campsites are continuously available for the selected dates.",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Clear dates" })[1]);
    expect(screen.getByText("Loop A Site 10")).toBeInTheDocument();

    // Combine search + non-matching date filter -> "Clear filters" resets both
    await user.type(
      screen.getByRole("searchbox", { name: "Search found campsites" }),
      "Loop A",
    );
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 15, 2027 — no openings/i,
      }),
    );
    expect(
      screen.getByText("No campsites match your search and selected dates."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "3 sites · 4 openings",
    );
  });

  it("re-anchors Grid view to the soonest opening when results arrive after an empty mount", async () => {
    const user = userEvent.setup();
    const emptyScan: ScanDetailResponse = {
      ...baseScan,
      start_date: "2027-06-01",
      end_date: "2027-08-30",
      last_checked_at: null,
      found_count: 0,
      results: [],
    };
    const { rerender } = render(
      <MemoryRouter>
        <FoundCampsites scan={emptyScan} />
      </MemoryRouter>,
    );

    // First check finishes with openings in August
    rerender(
      <MemoryRouter>
        <FoundCampsites
          scan={{
            ...emptyScan,
            last_checked_at: "2027-01-01T12:00:00Z",
            found_count: 1,
            results: [
              {
                ...baseScan.results[0],
                available_dates: ["2027-08-14", "2027-08-15"],
              },
            ],
          }}
        />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "Grid" }));
    expect(
      screen.getByRole("button", { name: /Loop A Site 10.*Aug 14, 2027/i }),
    ).toBeInTheDocument();
  });
});
