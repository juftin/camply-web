import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCampground, getScan } from "@/lib/api";
import type { Campground, ScanDetailResponse } from "@/lib/structs";
import { ScanDetail } from "./ScanDetail";

vi.mock("@/lib/api", () => ({ getScan: vi.fn(), getCampground: vi.fn() }));
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

/** Synthetic catalog metadata links to the campground rather than a site. */
const campground: Campground = {
  id: "camp-1",
  provider_id: 1,
  recreation_area_id: null,
  name: "Synthetic Pines",
  description: null,
  country: null,
  state: null,
  longitude: null,
  latitude: null,
  reservable: true,
  enabled: true,
  url: "https://book.example/entire-campground",
};

/** Render the scan route with optional cached availability for outage checks. */
const open = (cached?: ScanDetailResponse) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  });
  if (cached)
    client.setQueryData(["scans", "detail", "scan-1"], cached, {
      updatedAt: 1,
    });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/dashboard/scans/scan-1#results"]}>
        <Routes>
          <Route path="/dashboard/scans/:scanId" element={<ScanDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...view, client };
};

describe("Found campsites", () => {
  beforeEach(() => {
    vi.mocked(getScan).mockResolvedValue(scan);
    vi.mocked(getCampground).mockResolvedValue(campground);
  });

  it("shows separate date groups with site details and provider links", async () => {
    open();
    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });
    expect(within(results).getAllByText("Site 042")).toHaveLength(2);
    expect(within(results).getByText("Campsite 43")).toBeInTheDocument();
    expect(within(results).getAllByText("Electric hookup")).toHaveLength(2);
    expect(within(results).getAllByText("Accessible")).toHaveLength(2);
    const first = within(results).getByRole("group", {
      name: "Jul 1, 2027 – Jul 3, 2027",
    });
    const last = within(results).getByRole("group", {
      name: "Jul 5, 2027 – Jul 7, 2027",
    });
    expect(first).toHaveAttribute("open");
    expect(last).not.toHaveAttribute("open");
    expect(within(results).getAllByText("2 nights")).toHaveLength(3);
    expect(
      within(first).getByRole("link", { name: /view site 042 on provider/i }),
    ).toHaveAttribute("href", "https://book.example/camp");
    expect(
      within(results).getByText(/Availability can change/),
    ).toBeInTheDocument();
  });

  it("groups identical maximal stays and counts sites once across date groups", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [
        scan.results[0],
        {
          ...scan.results[1],
          available_dates: ["2027-07-01", "2027-07-02", "2027-07-08"],
        },
        {
          ...scan.results[1],
          campsite_id: "short",
          available_dates: ["2027-07-09"],
        },
      ],
    });
    open();
    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });
    expect(within(results).getAllByRole("group")).toHaveLength(2);
    const shared = within(results).getByRole("group", {
      name: "Jul 1, 2027 – Jul 3, 2027",
    });
    expect(within(shared).getAllByRole("listitem")).toHaveLength(2);
    expect(within(shared).getByText("Site 042")).toBeInTheDocument();
    expect(within(shared).getByText("Campsite 43")).toBeInTheDocument();
    expect(within(results).getByRole("status")).toHaveTextContent(
      "2 sites · 2 date ranges",
    );
    expect(
      within(results).queryByText("Campsite short"),
    ).not.toBeInTheDocument();
  });

  it("keeps ranges with the same check-in but different check-outs separate", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [
        scan.results[0],
        {
          ...scan.results[1],
          available_dates: ["2027-07-01", "2027-07-02", "2027-07-03"],
        },
      ],
    });
    open();
    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });
    expect(within(results).getAllByRole("group")).toHaveLength(3);
    const longer = within(results).getByRole("group", {
      name: "Jul 1, 2027 – Jul 4, 2027",
    });
    expect(within(longer).getByText("Campsite 43")).toBeInTheDocument();
    expect(within(longer).queryByText("Site 042")).not.toBeInTheDocument();
  });

  it("preserves expanded date groups when availability refreshes", async () => {
    const user = userEvent.setup();
    const { client } = open();
    const last = await screen.findByRole("group", {
      name: "Jul 5, 2027 – Jul 7, 2027",
    });
    const summary = last.querySelector("summary")!;
    await user.click(summary);
    expect(last).toHaveAttribute("open");
    act(() =>
      client.setQueryData(["scans", "detail", "scan-1"], {
        ...scan,
        last_checked_at: "2027-01-01T12:01:00Z",
      }),
    );
    expect(last).toHaveAttribute("open");
  });

  it("sorts date groups by longest stay and returns to soonest check-in", async () => {
    const user = userEvent.setup();
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [
        scan.results[0],
        {
          ...scan.results[1],
          available_dates: [
            "2027-07-02",
            "2027-07-03",
            "2027-07-04",
            "2027-07-05",
          ],
        },
      ],
    });
    open();
    const sort = await screen.findByRole("combobox", {
      name: "Sort date groups",
    });
    const results = screen.getByRole("region", { name: "Found campsites" });
    await user.selectOptions(sort, "longest");
    expect(within(results).getAllByRole("group")[0]).toHaveAccessibleName(
      "Jul 2, 2027 – Jul 6, 2027",
    );
    await user.selectOptions(sort, "soonest");
    expect(within(results).getAllByRole("group")[0]).toHaveAccessibleName(
      "Jul 1, 2027 – Jul 3, 2027",
    );
  });

  it("links to the full campground separately from site booking actions", async () => {
    open();
    const link = await screen.findByRole("link", {
      name: "View campground on provider",
    });
    expect(getCampground).toHaveBeenCalledWith(1, "camp-1");
    expect(link).toHaveAttribute("href", campground.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(
      screen.getByRole("region", { name: "Found campsites" }),
    ).not.toContainElement(link);
  });

  it("keeps availability usable when campground metadata cannot load", async () => {
    vi.mocked(getCampground).mockRejectedValue(
      new Error("Catalog unavailable"),
    );
    open();
    expect(
      await screen.findByRole("region", { name: "Found campsites" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "View campground on provider" }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByText("Site 042")).toHaveLength(2);
  });

  it("searches sites and lets users clear an empty search", async () => {
    const user = userEvent.setup();
    open();
    await user.type(
      await screen.findByRole("searchbox", { name: "Search found campsites" }),
      "042",
    );
    expect(screen.queryByText("Campsite 43")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "1 site · 2 date ranges",
    );
    expect(
      screen
        .getAllByRole("group")
        .filter((group) => group.hasAttribute("open")),
    ).toHaveLength(2);
    await user.clear(screen.getByRole("searchbox"));
    await user.type(screen.getByRole("searchbox"), "missing");
    expect(
      screen.getByText("No campsites match your search."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getAllByText("Site 042")).toHaveLength(2);
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
    expect(
      await screen.findByRole("link", { name: "View campground on provider" }),
    ).toHaveAttribute("href", campground.url);
  });

  it("keeps cached matches visible when a refresh fails", async () => {
    vi.mocked(getScan).mockRejectedValue(new Error("Network unavailable"));
    open(scan);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not refresh availability",
    );
    expect(screen.getAllByText("Site 042")).toHaveLength(2);
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
