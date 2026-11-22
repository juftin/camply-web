import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCampground, getScan } from "@/lib/api";
import type { Campground, ScanDetailResponse } from "@/lib/structs";
import { ScanDetail } from "./ScanDetail";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    isReady: true,
    user: {
      id: "user-1",
      email: "camper@example.test",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
    },
  }),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getScan: vi.fn(),
  getCampground: vi.fn(),
}));
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
      provider_id: 1,
      campground_id: "camp-1",
      campground_name: "Synthetic Pines",
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
      provider_id: 1,
      campground_id: "camp-1",
      campground_name: "Synthetic Pines",
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

const open = (cached?: ScanDetailResponse) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  });
  if (cached) {
    client.setQueryData(["scans", "detail", "scan-1"], cached, {
      updatedAt: 1,
    });
  }
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

describe("ScanDetail & Found campsites", () => {
  beforeEach(() => {
    vi.mocked(getScan).mockResolvedValue(scan);
    vi.mocked(getCampground).mockResolvedValue(campground);
  });

  it("renders a single cohesive header without a duplicate Scan overview card", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      allowed_weekdays: [0, 2],
      min_rv_length: 28,
      require_accessible: true,
      require_electric: true,
    });
    open();

    expect(await screen.findByText("Monday, Wednesday")).toBeInTheDocument();
    expect(screen.getByText("Min 28 ft")).toBeInTheDocument();
    expect(screen.getByText("ADA accessible")).toBeInTheDocument();
    expect(screen.getByText("Electric required")).toBeInTheDocument();
    expect(screen.queryByText("Scan overview")).not.toBeInTheDocument();
  });

  it("describes unrestricted scans as Any night", async () => {
    open();
    expect(await screen.findByText("Any night")).toBeInTheDocument();
  });

  it("shows deduplicated site cards with stays, capabilities, and provider booking links", async () => {
    open();
    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });

    // Site 042 has two stays (Jul 1-3, Jul 5-7) and appears once
    expect(within(results).getAllByText("Site 042")).toHaveLength(1);
    expect(within(results).getByText("Campsite 43")).toBeInTheDocument();
    expect(within(results).getByText("Electric hookup")).toBeInTheDocument();
    expect(within(results).getByText("Accessible")).toBeInTheDocument();
    expect(within(results).getByRole("status")).toHaveTextContent(
      "2 sites · 3 openings",
    );
    expect(
      within(results).getByRole("link", {
        name: /view site 042 on provider website/i,
      }),
    ).toHaveAttribute("href", "https://book.example/camp");
    expect(
      within(results).getAllByText(/Availability can change/),
    ).toHaveLength(1);
  });

  it("excludes stays shorter than min_stay_length and counts unique sites accurately", async () => {
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
    expect(within(results).getByRole("status")).toHaveTextContent(
      "2 sites · 3 openings",
    );
    expect(
      within(results).queryByText("Campsite short"),
    ).not.toBeInTheDocument();
  });

  it("preserves view mode, search query, and calendar filter when availability refreshes", async () => {
    const user = userEvent.setup();
    const { client } = open();

    const results = await screen.findByRole("region", {
      name: "Found campsites",
    });
    const calendar = within(results).getByRole("region", {
      name: "Availability calendar",
    });
    await user.click(
      within(calendar).getByRole("button", {
        name: /Jul 2, 2027 — 2 sites available/i,
      }),
    );
    await user.click(within(results).getByRole("button", { name: "Grid" }));

    act(() =>
      client.setQueryData(["scans", "detail", "scan-1"], {
        ...scan,
        last_checked_at: "2027-01-01T12:01:00Z",
      }),
    );

    expect(
      within(results).getByRole("button", { name: "Grid" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(within(results).getByText(/Filtered dates:/i)).toBeInTheDocument();
  });

  it("links to the full campground in the header separately from site booking actions", async () => {
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
    expect(screen.getByText("Site 042")).toBeInTheDocument();
  });

  it("clamps pagination cleanly when campsites disappear and later return", async () => {
    const user = userEvent.setup();
    const largeScan: ScanDetailResponse = {
      ...scan,
      found_count: 12,
      results: Array.from({ length: 12 }, (_, index) => ({
        ...scan.results[0],
        campsite_id: `site-${index + 1}`,
        campsite_name: `Synthetic site ${index + 1}`,
        available_dates: ["2027-07-01", "2027-07-02"],
      })),
    };
    vi.mocked(getScan).mockResolvedValue(largeScan);
    const { client } = open();

    await user.click(
      await screen.findByRole("button", { name: "Next campsites" }),
    );
    expect(screen.getByText("Synthetic site 11")).toBeInTheDocument();

    vi.mocked(getScan).mockResolvedValue({
      ...largeScan,
      results: largeScan.results.slice(0, 2),
    });
    await act(async () => {
      await client.invalidateQueries({
        queryKey: ["scans", "detail", "scan-1"],
      });
    });

    expect(await screen.findByText("Synthetic site 1")).toBeInTheDocument();
    expect(screen.queryByText("Synthetic site 11")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Next campsites" }),
    ).not.toBeInTheDocument();

    vi.mocked(getScan).mockResolvedValue(largeScan);
    await act(async () => {
      await client.invalidateQueries({
        queryKey: ["scans", "detail", "scan-1"],
      });
    });

    expect(screen.getByText("Synthetic site 1")).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Previous campsites" }),
    ).toBeDisabled();
  });

  it("shows waiting, paused, and cached-error states appropriately", async () => {
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [],
      found_count: 0,
      last_checked_at: null,
    });
    const firstView = open();
    expect(
      await screen.findByText("Waiting for the first check"),
    ).toBeInTheDocument();
    firstView.unmount();

    vi.mocked(getScan).mockResolvedValue({ ...scan, is_active: false });
    const pausedView = open();
    expect(
      await screen.findByText(/availability is not being refreshed/),
    ).toBeInTheDocument();
    pausedView.unmount();

    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [],
      found_count: 0,
      is_active: false,
    });
    const pausedEmptyView = open();
    expect(
      await screen.findByText("No matching campsites right now"),
    ).toBeInTheDocument();
    expect(screen.getByText(/This scan is paused/)).toBeInTheDocument();
    pausedEmptyView.unmount();

    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      results: [],
      found_count: 0,
      is_active: true,
    });
    const activeEmptyView = open();
    expect(
      await screen.findByText("No matching campsites right now"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Camply will notify you when new openings match/i),
    ).toBeInTheDocument();
    activeEmptyView.unmount();

    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      destination_type: "recreation_area",
      destination_name: "Synthetic Basin",
      campground_id: null,
      campground_name: null,
      recreation_area_id: "area-1",
      coverage_status: "partial",
      results: [],
      found_count: 0,
      is_active: true,
    });
    const partialAreaEmptyView = open();
    expect(
      await screen.findByText(
        "No matching campsites in checked campgrounds yet",
      ),
    ).toBeInTheDocument();
    partialAreaEmptyView.unmount();

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

  it("renders structured recreation-area coverage with relative timestamps and stale-attributed results", async () => {
    const user = userEvent.setup();
    vi.mocked(getScan).mockResolvedValue({
      ...scan,
      destination_type: "recreation_area",
      destination_name: "Synthetic Basin",
      campground_id: null,
      campground_name: null,
      recreation_area_id: "area-1",
      recreation_area_name: "Synthetic Basin",
      coverage_mode: "selected",
      campground_ids: ["cg-a", "cg-b"],
      eligible_campground_count: 1,
      unavailable_selection_count: 1,
      matching_campground_count: 1,
      checked_campground_count: 1,
      pending_campground_count: 0,
      failed_campground_count: 1,
      coverage_status: "partial",
      campgrounds: [
        {
          provider_id: 1,
          campground_id: "cg-a",
          campground_name: "North Pine",
          eligible: true,
          outcome: "success",
          last_checked_at: "2027-01-01T11:50:00Z",
        },
        {
          provider_id: 1,
          campground_id: "cg-b",
          campground_name: "Closed Creek",
          eligible: false,
          outcome: "failed",
          unavailable_reason:
            "Campground is no longer eligible in this recreation area",
        },
      ],
      results: [
        {
          provider_id: 1,
          campground_id: "cg-a",
          campground_name: "North Pine",
          campsite_id: "001",
          campsite_name: "Site 001",
          campsite_type: "TENT",
          is_electric: false,
          is_accessible: false,
          booking_url: "https://book.example/north-pine",
          available_dates: ["2027-07-01", "2027-07-02"],
          is_stale: true,
        },
      ],
    });
    open();

    const coverage = await screen.findByRole("region", {
      name: "Campground coverage",
    });
    expect(
      within(coverage).getByText("Selected campgrounds"),
    ).toBeInTheDocument();
    expect(within(coverage).getByText("1 eligible")).toBeInTheDocument();
    expect(within(coverage).getByText("1 unavailable")).toBeInTheDocument();
    expect(
      within(coverage).getByText(
        /Results may be incomplete; some campgrounds are unchecked or failed/,
      ),
    ).toBeInTheDocument();

    await user.click(within(coverage).getByText(/Campground status details/i));
    expect(within(coverage).getByText("Closed Creek")).toBeInTheDocument();
    expect(
      within(coverage).queryByText(/2027-01-01T11:50:00Z/),
    ).not.toBeInTheDocument();

    const results = screen.getByRole("region", { name: "Found campsites" });
    expect(within(results).getByText("North Pine")).toBeInTheDocument();
    expect(within(results).getByText(/Stale/i)).toBeInTheDocument();
  });
});
