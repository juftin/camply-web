import { describe, expect, it } from "vitest";
import type { ScanResultItem } from "@/lib/structs";
import {
  applyCalendarDayClick,
  availableStays,
  buildCalendarMonth,
  buildGridWindow,
  filterAndSortSites,
  filterSitesBySearch,
  formatDateSelectionSummary,
  formatStayDate,
  getCalendarMonthBounds,
  getInitialCalendarMonth,
  normalizeFoundSites,
  stayMatchesSelection,
} from "./availability";

const makeResult = (overrides: Partial<ScanResultItem>): ScanResultItem => ({
  provider_id: 1,
  campground_id: "cg-1",
  campground_name: "Upper Pines",
  campsite_id: "10",
  campsite_name: "Site 010",
  campsite_type: "TENT",
  is_electric: false,
  is_accessible: false,
  permitted_equipment: [],
  max_vehicle_length: null,
  available_dates: ["2027-07-01", "2027-07-02"],
  booking_url: "https://book.example/cg-1",
  is_stale: false,
  ...overrides,
});

describe("availableStays", () => {
  it("groups consecutive nights into maximal stays with exclusive check-out", () => {
    const stays = availableStays(
      ["2027-07-06", "2027-07-02", "2027-07-01", "2027-07-05", "2027-07-01"],
      2,
    );
    expect(stays).toEqual([
      {
        start: "2027-07-01",
        end: "2027-07-03",
        nights: 2,
        dates: ["2027-07-01", "2027-07-02"],
      },
      {
        start: "2027-07-05",
        end: "2027-07-07",
        nights: 2,
        dates: ["2027-07-05", "2027-07-06"],
      },
    ]);
  });

  it("drops blocks shorter than minStayLength", () => {
    const stays = availableStays(
      ["2027-07-01", "2027-07-04", "2027-07-05", "2027-07-06"],
      3,
    );
    expect(stays).toHaveLength(1);
    expect(stays[0]).toMatchObject({
      start: "2027-07-04",
      end: "2027-07-07",
      nights: 3,
    });
  });
});

describe("normalizeFoundSites", () => {
  it("deduplicates by (provider, campground, campsite) without merging across campgrounds", () => {
    const sites = normalizeFoundSites(
      [
        makeResult({
          campground_id: "cg-a",
          campground_name: "North Pines",
          campsite_id: "001",
          campsite_name: "Site 001",
          available_dates: ["2027-07-01", "2027-07-02"],
        }),
        makeResult({
          campground_id: "cg-b",
          campground_name: "Lower Pines",
          campsite_id: "001",
          campsite_name: "Site 001",
          available_dates: ["2027-07-03", "2027-07-04"],
        }),
        makeResult({
          campground_id: "cg-a",
          campground_name: "North Pines",
          campsite_id: "001",
          campsite_name: "Site 001",
          available_dates: ["2027-07-05", "2027-07-06"],
          is_stale: true,
        }),
      ],
      2,
    );

    expect(sites).toHaveLength(2);
    const north = sites.find((s) => s.key === "1:cg-a:001")!;
    const lower = sites.find((s) => s.key === "1:cg-b:001")!;
    expect(north.stays).toHaveLength(2);
    expect(north.totalAvailableNights).toBe(4);
    expect(north.isStale).toBe(true);
    expect(lower.stays).toHaveLength(1);
    expect(lower.totalAvailableNights).toBe(2);
  });

  it("falls back to Campsite <id> when campsite_name is blank and excludes non-qualifying sites", () => {
    const sites = normalizeFoundSites(
      [
        makeResult({
          campsite_id: "43",
          campsite_name: "   ",
          available_dates: ["2027-07-02", "2027-07-03"],
        }),
        makeResult({
          campsite_id: "short",
          campsite_name: "Short Site",
          available_dates: ["2027-07-09"],
        }),
      ],
      2,
    );
    expect(sites).toHaveLength(1);
    expect(sites[0].displayName).toBe("Campsite 43");
  });
});

describe("calendar date selection & matching", () => {
  it("handles single night, same-day clear, forward range, reverse normalization, and restart", () => {
    const s1 = applyCalendarDayClick(
      null,
      "2027-07-02",
      "2027-07-01",
      "2027-07-10",
    );
    expect(s1).toEqual({ start: "2027-07-02", end: null });

    // Clicking the same date clears
    expect(
      applyCalendarDayClick(s1, "2027-07-02", "2027-07-01", "2027-07-10"),
    ).toBeNull();

    // Forward range including scan.end_date checkout boundary
    const s2 = applyCalendarDayClick(
      s1,
      "2027-07-10",
      "2027-07-01",
      "2027-07-10",
    );
    expect(s2).toEqual({ start: "2027-07-02", end: "2027-07-10" });

    // Reverse click normalizes start < end
    const sRev = applyCalendarDayClick(
      { start: "2027-07-05", end: null },
      "2027-07-02",
      "2027-07-01",
      "2027-07-10",
    );
    expect(sRev).toEqual({ start: "2027-07-02", end: "2027-07-05" });

    // Clicking while a range is active starts a fresh single-night selection
    const sNext = applyCalendarDayClick(
      s2,
      "2027-07-04",
      "2027-07-01",
      "2027-07-10",
    );
    expect(sNext).toEqual({ start: "2027-07-04", end: null });

    // Clicking end_date when unselected is ignored (not an occupied night)
    expect(
      applyCalendarDayClick(null, "2027-07-10", "2027-07-01", "2027-07-10"),
    ).toBeNull();
  });

  it("matches overlapping stays for single night and requires continuous coverage for ranges", () => {
    const stayA = availableStays(["2027-07-01", "2027-07-02"], 2)[0]; // Jul 1 -> Jul 3
    const stayB = availableStays(
      ["2027-07-01", "2027-07-02", "2027-07-03", "2027-07-04"],
      2,
    )[0]; // Jul 1 -> Jul 5
    const stayC = availableStays(["2027-07-02", "2027-07-03"], 2)[0]; // Jul 2 -> Jul 4

    const singleJul2 = { start: "2027-07-02", end: null };
    expect(stayMatchesSelection(stayA, singleJul2)).toBe(true);
    expect(stayMatchesSelection(stayB, singleJul2)).toBe(true);
    expect(stayMatchesSelection(stayC, singleJul2)).toBe(true);

    const rangeJul2To4 = { start: "2027-07-02", end: "2027-07-04" };
    expect(stayMatchesSelection(stayA, rangeJul2To4)).toBe(false);
    expect(stayMatchesSelection(stayB, rangeJul2To4)).toBe(true);
    expect(stayMatchesSelection(stayC, rangeJul2To4)).toBe(true);
  });
});

describe("buildCalendarMonth & month helpers", () => {
  it("anchors to soonest opening month and falls back to scan start when empty", () => {
    const sites = normalizeFoundSites(
      [
        makeResult({
          available_dates: ["2027-08-14", "2027-08-15"],
        }),
      ],
      2,
    );
    expect(getInitialCalendarMonth(sites, "2027-06-01")).toEqual({
      year: 2027,
      month: 7, // August (0-indexed)
    });
    expect(getInitialCalendarMonth([], "2027-06-01")).toEqual({
      year: 2027,
      month: 5, // June
    });
    expect(getCalendarMonthBounds("2027-06-01", "2027-09-05")).toEqual({
      min: { year: 2027, month: 5 },
      max: { year: 2027, month: 8 },
    });
  });

  it("computes per-night counts from passed search-filtered sites, Fri/Sat weekend flags, and checkout-boundary selectability", () => {
    const sites = normalizeFoundSites(
      [
        makeResult({
          campsite_id: "1",
          campsite_name: "RV Site 1",
          campsite_type: "RV",
          available_dates: ["2027-07-02", "2027-07-03"], // Fri Jul 2, Sat Jul 3
        }),
        makeResult({
          campsite_id: "2",
          campsite_name: "Tent Site 2",
          campsite_type: "TENT",
          available_dates: ["2027-07-02", "2027-07-03"],
        }),
      ],
      2,
    );

    const rvOnly = filterSitesBySearch(sites, "rv");
    const monthUnselected = buildCalendarMonth(
      2027,
      6, // July
      "2027-07-01",
      "2027-07-04",
      rvOnly,
      null,
    );
    const jul2 = monthUnselected.days.find((d) => d.date === "2027-07-02")!;
    const jul3 = monthUnselected.days.find((d) => d.date === "2027-07-03")!;
    const jul4 = monthUnselected.days.find((d) => d.date === "2027-07-04")!;

    expect(jul2.availableSiteCount).toBe(1);
    expect(jul2.isWeekendNight).toBe(true); // Friday
    expect(jul3.isWeekendNight).toBe(true); // Saturday
    expect(jul4.isCheckoutBoundary).toBe(true);
    expect(jul4.isSelectable).toBe(false); // Disabled until start date picked

    const monthStartPicked = buildCalendarMonth(
      2027,
      6,
      "2027-07-01",
      "2027-07-04",
      rvOnly,
      { start: "2027-07-02", end: null },
    );
    const jul4WithStart = monthStartPicked.days.find(
      (d) => d.date === "2027-07-04",
    )!;
    expect(jul4WithStart.isSelectable).toBe(true);
  });
});

describe("filterAndSortSites", () => {
  const sites = normalizeFoundSites(
    [
      makeResult({
        campsite_id: "10",
        campsite_name: "Site 10",
        available_dates: [
          "2027-07-01",
          "2027-07-02",
          "2027-07-15",
          "2027-07-16",
        ], // 4 total nights; Jul 1-3 (2n) & Jul 15-17 (2n)
      }),
      makeResult({
        campsite_id: "2",
        campsite_name: "Site 2",
        available_dates: [
          "2027-07-14",
          "2027-07-15",
          "2027-07-16",
          "2027-07-17",
        ], // 4 total nights; Jul 14-18 (4n)
      }),
      makeResult({
        campsite_id: "5",
        campsite_name: "Site 5",
        available_dates: [
          "2027-07-05",
          "2027-07-06",
          "2027-07-07",
          "2027-07-08",
          "2027-07-09",
        ], // 5 total nights; Jul 5-10 (5n)
      }),
    ],
    2,
  );

  it("sorts by soonest, longest, most_nights, and natural site name", () => {
    expect(
      filterAndSortSites(sites, "", null, "soonest", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["10", "5", "2"]);

    expect(
      filterAndSortSites(sites, "", null, "longest", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["5", "2", "10"]);

    expect(
      filterAndSortSites(sites, "", null, "most_nights", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["5", "10", "2"]);

    expect(
      filterAndSortSites(sites, "", null, "name", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["2", "5", "10"]);
  });

  it("evaluates matching stays for soonest and longest when a calendar date filter is active", () => {
    const sel = { start: "2027-07-15", end: null };
    // Matching stays on Jul 15: Site 2 has Jul 14-18 (4n, starts Jul 14); Site 10 has Jul 15-17 (2n, starts Jul 15)
    expect(
      filterAndSortSites(sites, "", sel, "soonest", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["2", "10"]);

    expect(
      filterAndSortSites(sites, "", sel, "longest", false).map(
        (r) => r.site.campsiteId,
      ),
    ).toEqual(["2", "10"]);
  });
});

describe("buildGridWindow & formatting", () => {
  it("clamps a 14-day window inside scan occupied nights and exposes prev/next flags", () => {
    const shortWin = buildGridWindow("2027-07-01", "2027-07-06", null, 14);
    expect(shortWin.dates).toEqual([
      "2027-07-01",
      "2027-07-02",
      "2027-07-03",
      "2027-07-04",
      "2027-07-05",
    ]);
    expect(shortWin.canPrev).toBe(false);
    expect(shortWin.canNext).toBe(false);

    const midWin = buildGridWindow(
      "2027-07-01",
      "2027-08-10",
      "2027-07-10",
      14,
    );
    expect(midWin.dates).toHaveLength(14);
    expect(midWin.startDate).toBe("2027-07-10");
    expect(midWin.endDate).toBe("2027-07-23");
    expect(midWin.canPrev).toBe(true);
    expect(midWin.canNext).toBe(true);

    const endWin = buildGridWindow(
      "2027-07-01",
      "2027-08-10",
      "2027-08-05",
      14,
    );
    expect(endWin.startDate).toBe("2027-07-27");
    expect(endWin.endDate).toBe("2027-08-09");
    expect(endWin.canPrev).toBe(true);
    expect(endWin.canNext).toBe(false);
  });

  it("formats stay dates and selection summaries cleanly including cross-year dates", () => {
    expect(formatStayDate("2027-12-31", true)).toContain("2027");
    expect(
      formatDateSelectionSummary({ start: "2027-07-02", end: null }),
    ).toMatch(/Jul 2/);
    expect(
      formatDateSelectionSummary({ start: "2027-07-02", end: "2027-07-04" }),
    ).toContain("2 nights");
  });
});
