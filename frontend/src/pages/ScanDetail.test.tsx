import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getScan } from "@/lib/api";
import type { ScanDetailResponse } from "@/lib/structs";
import { ScanDetail } from "./ScanDetail";

vi.mock("@/lib/api", () => ({ getScan: vi.fn() }));
vi.mock("@/components/ScanForm", () => ({ ScanForm: () => null }));

const scan: ScanDetailResponse = {
  id: "scan-1",
  provider_id: 1,
  campground_id: "camp-1",
  campground_name: "Synthetic Pines",
  recreation_area_name: "Synthetic Park",
  start_date: "2027-07-01",
  end_date: "2027-07-10",
  is_active: true,
  min_stay_length: 2,
  preferred_types: [],
  require_electric: false,
  found_count: 2,
  last_checked_at: "2027-01-01T12:00:00Z",
  created_at: "2027-01-01T00:00:00Z",
  results: [
    {
      campsite_id: "42",
      campsite_name: "Site 042",
      campsite_type: "RV",
      is_electric: true,
      is_accessible: true,
      booking_url: "https://book.example/camp",
      available_dates: [
        "2027-07-06",
        "2027-07-02",
        "2027-07-01",
        "2027-07-05",
        "2027-07-01",
      ],
    },
    {
      campsite_id: "43",
      campsite_name: "",
      campsite_type: null,
      is_electric: null,
      is_accessible: null,
      booking_url: "",
      available_dates: ["2027-07-02", "2027-07-03"],
    },
  ],
};

const open = (cached?: ScanDetailResponse) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  });
  if (cached)
    client.setQueryData(["scans", "detail", "scan-1"], cached, {
      updatedAt: 1,
    });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/dashboard/scans/scan-1#results"]}>
        <Routes>
          <Route path="/dashboard/scans/:scanId" element={<ScanDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("Found campsites", () => {
  beforeEach(() => {
    vi.mocked(getScan).mockResolvedValue(scan);
  });

  it("shows separate stays with check-out dates, site details and booking links", async () => {
    open();
    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });
    expect(within(results).getByText("Site 042")).toBeInTheDocument();
    expect(within(results).getByText("Campsite 43")).toBeInTheDocument();
    expect(within(results).getByText("Electric hookup")).toBeInTheDocument();
    expect(within(results).getByText("Accessible")).toBeInTheDocument();
    expect(
      within(results).getByText("Jul 1, 2027 – Jul 3, 2027"),
    ).toBeInTheDocument();
    expect(
      within(results).getByText("Jul 5, 2027 – Jul 7, 2027"),
    ).toBeInTheDocument();
    expect(within(results).getAllByText("2 nights")).toHaveLength(3);
    expect(
      within(results).getByRole("link", { name: /book site 042/i }),
    ).toHaveAttribute("href", "https://book.example/camp");
    expect(
      within(results).getByText(/Availability can change/),
    ).toBeInTheDocument();
  });

  it("searches sites and lets users clear an empty search", async () => {
    const user = userEvent.setup();
    open();
    await user.type(
      await screen.findByRole("searchbox", { name: "Search found campsites" }),
      "042",
    );
    expect(screen.queryByText("Campsite 43")).not.toBeInTheDocument();
    expect(screen.getByText("1 of 2 campsites")).toBeInTheDocument();
    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "missing");
    expect(
      screen.getByText("No campsites match your search."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getByText("Site 042")).toBeInTheDocument();
  });

  it("shows a waiting state before the first check", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [],
      found_count: 0,
      last_checked_at: null,
    });
    open();
    expect(
      await screen.findByText("Waiting for the first check"),
    ).toBeInTheDocument();
  });

  it("shows a checked empty state for paused scans", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [],
      found_count: 0,
      is_active: false,
    });
    open();
    expect(
      await screen.findByText("No matching campsites right now"),
    ).toBeInTheDocument();
    expect(screen.getByText(/This scan is paused/)).toBeInTheDocument();
  });

  it("keeps cached matches visible when a refresh fails", async () => {
    vi.mocked(getScan).mockRejectedValue(new Error("Network unavailable"));
    open(scan);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not refresh availability",
    );
    expect(screen.getByText("Site 042")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
  });

  it("offers retry when results fail to load", async () => {
    vi.mocked(getScan).mockRejectedValue(new Error("Network unavailable"));
    open();
    expect(
      await screen.findByRole(
        "button",
        { name: "Try again" },
        { timeout: 3000 },
      ),
    ).toBeInTheDocument();
  });
});
