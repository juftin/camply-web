import type { ScanResultItem } from "@/lib/structs";
import {
  addDays,
  daysBetween,
  parseIsoDate,
  toIsoDateString,
} from "@/lib/utils";

export const SITES_PER_PAGE = 10;
export const MAX_INITIAL_STAYS = 4;
export const GRID_WINDOW_DAYS = 14;

/** A maximal contiguous block of occupied nights with an exclusive check-out date. */
export interface AvailableStay {
  start: string;
  end: string;
  nights: number;
  dates: string[];
}

/** One deduplicated campsite with derived qualifying stays and capability metadata. */
export interface NormalizedFoundSite {
  key: string;
  providerId: number;
  campgroundId: string;
  campgroundName: string;
  campsiteId: string;
  displayName: string;
  campsiteType: string | null;
  isElectric: boolean | null;
  isAccessible: boolean | null;
  maxVehicleLength: number | null;
  permittedEquipment: string[];
  bookingUrl: string;
  lastCheckedAt: string | null;
  isStale: boolean;
  stays: AvailableStay[];
  availableNightSet: ReadonlySet<string>;
  soonestCheckIn: string;
  longestStayNights: number;
  totalAvailableNights: number;
  searchText: string;
}

/** Active calendar date filter: single occupied night or exclusive check-out stay range. */
export type DateSelection =
  | null
  | { start: string; end: null }
  | { start: string; end: string };

export interface MonthRef {
  year: number;
  month: number; // 0-indexed (0 = Jan .. 11 = Dec)
}

export interface CalendarDayCell {
  date: string;
  dayNumber: number;
  isCurrentMonth: boolean;
  isInScanWindow: boolean;
  isCheckoutBoundary: boolean;
  isWeekendNight: boolean;
  availableSiteCount: number;
  isSelectable: boolean;
}

export interface CalendarMonth {
  year: number;
  month: number;
  label: string;
  days: CalendarDayCell[];
}

export type FoundViewMode = "cards" | "grid";
export type FoundSortMode = "soonest" | "longest" | "most_nights" | "name";

export interface FilteredFoundSite {
  site: NormalizedFoundSite;
  matchingStays: AvailableStay[];
  matchingStayKeys: ReadonlySet<string>;
}

export interface GridWindow {
  dates: string[];
  startDate: string;
  endDate: string;
  canPrev: boolean;
  canNext: boolean;
}

export type SelectedGridStay = {
  siteKey: string;
  stayStart: string;
  stayEnd: string;
} | null;

export function stayKey(stay: Pick<AvailableStay, "start" | "end">): string {
  return `${stay.start}/${stay.end}`;
}

/** Turn available occupied nights into maximal consecutive stays meeting minStayLength. */
export function availableStays(
  dates: string[],
  minStayLength = 1,
): AvailableStay[] {
  const minNights = Math.max(1, minStayLength);
  const blocks: AvailableStay[] = [];
  for (const date of [...new Set(dates)].sort()) {
    const previous = blocks[blocks.length - 1];
    if (previous?.end === date) {
      previous.end = addDays(date, 1);
      previous.nights += 1;
      previous.dates.push(date);
    } else {
      blocks.push({
        start: date,
        end: addDays(date, 1),
        nights: 1,
        dates: [date],
      });
    }
  }
  return blocks.filter((block) => block.nights >= minNights);
}

/** Deduplicate scan results by (provider, campground, campsite) and compute qualifying stays. */
export function normalizeFoundSites(
  results: ScanResultItem[],
  minStayLength: number,
): NormalizedFoundSite[] {
  const merged = new Map<
    string,
    { item: ScanResultItem; dates: Set<string>; isStale: boolean }
  >();

  for (const item of results) {
    const providerId = item.provider_id ?? 0;
    const campgroundId = item.campground_id ?? "";
    const key = `${providerId}:${campgroundId}:${item.campsite_id}`;
    const existing = merged.get(key);
    if (existing) {
      for (const d of item.available_dates ?? []) existing.dates.add(d);
      existing.isStale = existing.isStale || Boolean(item.is_stale);
      if (!existing.item.campsite_name.trim() && item.campsite_name.trim()) {
        existing.item = { ...existing.item, campsite_name: item.campsite_name };
      }
      if (!existing.item.booking_url && item.booking_url) {
        existing.item = { ...existing.item, booking_url: item.booking_url };
      }
    } else {
      merged.set(key, {
        item,
        dates: new Set(item.available_dates ?? []),
        isStale: Boolean(item.is_stale),
      });
    }
  }

  const sites: NormalizedFoundSite[] = [];
  for (const [key, entry] of merged) {
    const stays = availableStays([...entry.dates], minStayLength);
    if (stays.length === 0) continue;

    const { item } = entry;
    const displayName =
      item.campsite_name?.trim() || `Campsite ${item.campsite_id}`;
    const campgroundName = item.campground_name?.trim() || "";
    const availableNightSet = new Set<string>();
    let longestStayNights = 0;
    let totalAvailableNights = 0;

    for (const stay of stays) {
      if (stay.nights > longestStayNights) longestStayNights = stay.nights;
      totalAvailableNights += stay.nights;
      for (const date of stay.dates) availableNightSet.add(date);
    }

    sites.push({
      key,
      providerId: item.provider_id ?? 0,
      campgroundId: item.campground_id ?? "",
      campgroundName,
      campsiteId: item.campsite_id,
      displayName,
      campsiteType: item.campsite_type ?? null,
      isElectric: item.is_electric ?? null,
      isAccessible: item.is_accessible ?? null,
      maxVehicleLength: item.max_vehicle_length ?? null,
      permittedEquipment: item.permitted_equipment ?? [],
      bookingUrl: item.booking_url ?? "",
      lastCheckedAt: item.last_checked_at ?? null,
      isStale: entry.isStale,
      stays,
      availableNightSet,
      soonestCheckIn: stays[0].start,
      longestStayNights,
      totalAvailableNights,
      searchText:
        `${campgroundName} ${displayName} ${item.campsite_id} ${item.campsite_type ?? ""}`.toLowerCase(),
    });
  }

  return sites;
}

/** Apply progressive calendar click semantics: single night -> normalized check-in/check-out range. */
export function applyCalendarDayClick(
  prev: DateSelection,
  clickedDate: string,
  scanStart: string,
  scanEnd: string,
): DateSelection {
  const isOccupiedInWindow = clickedDate >= scanStart && clickedDate < scanEnd;
  const isCheckoutBoundary = clickedDate === scanEnd;

  if (prev === null) {
    return isOccupiedInWindow ? { start: clickedDate, end: null } : null;
  }

  if (prev.end === null) {
    if (clickedDate === prev.start) {
      return null;
    }
    if (
      clickedDate > prev.start &&
      (isOccupiedInWindow || isCheckoutBoundary)
    ) {
      return { start: prev.start, end: clickedDate };
    }
    if (clickedDate < prev.start && isOccupiedInWindow) {
      return { start: clickedDate, end: prev.start };
    }
    return prev;
  }

  return isOccupiedInWindow ? { start: clickedDate, end: null } : prev;
}

/** Check whether a single qualifying stay satisfies the active calendar selection. */
export function stayMatchesSelection(
  stay: AvailableStay,
  selection: DateSelection,
): boolean {
  if (selection === null) return true;
  if (selection.end === null) {
    return stay.start <= selection.start && selection.start < stay.end;
  }
  return stay.start <= selection.start && stay.end >= selection.end;
}

export function filterSitesBySearch(
  sites: NormalizedFoundSite[],
  query: string,
): NormalizedFoundSite[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return sites;
  return sites.filter((site) => site.searchText.includes(normalized));
}

function compareSiteNames(
  a: NormalizedFoundSite,
  b: NormalizedFoundSite,
  isMultiCampground: boolean,
): number {
  if (isMultiCampground) {
    const cgCompare = a.campgroundName.localeCompare(
      b.campgroundName,
      undefined,
      {
        numeric: true,
        sensitivity: "base",
      },
    );
    if (cgCompare !== 0) return cgCompare;
  }
  const nameCompare = a.displayName.localeCompare(b.displayName, undefined, {
    numeric: true,
    sensitivity: "base",
  });
  if (nameCompare !== 0) return nameCompare;
  return a.campsiteId.localeCompare(b.campsiteId, undefined, { numeric: true });
}

/** Filter normalized sites by text search and date selection, then sort deterministically. */
export function filterAndSortSites(
  sites: NormalizedFoundSite[],
  query: string,
  selection: DateSelection,
  sortMode: FoundSortMode,
  isMultiCampground: boolean,
): FilteredFoundSite[] {
  const searchFiltered = filterSitesBySearch(sites, query);
  const matched: FilteredFoundSite[] = [];

  for (const site of searchFiltered) {
    const matchingStays =
      selection === null
        ? site.stays
        : site.stays.filter((stay) => stayMatchesSelection(stay, selection));
    if (matchingStays.length === 0) continue;

    matched.push({
      site,
      matchingStays,
      matchingStayKeys: new Set(matchingStays.map((s) => stayKey(s))),
    });
  }

  const effectiveSoonest = (entry: FilteredFoundSite) =>
    selection === null
      ? entry.site.soonestCheckIn
      : entry.matchingStays[0].start;
  const effectiveLongest = (entry: FilteredFoundSite) =>
    selection === null
      ? entry.site.longestStayNights
      : Math.max(...entry.matchingStays.map((s) => s.nights));

  return matched.sort((a, b) => {
    switch (sortMode) {
      case "longest": {
        const diff = effectiveLongest(b) - effectiveLongest(a);
        if (diff !== 0) return diff;
        const soonestDiff = effectiveSoonest(a).localeCompare(
          effectiveSoonest(b),
        );
        if (soonestDiff !== 0) return soonestDiff;
        return compareSiteNames(a.site, b.site, isMultiCampground);
      }
      case "most_nights": {
        const diff = b.site.totalAvailableNights - a.site.totalAvailableNights;
        if (diff !== 0) return diff;
        const soonestDiff = effectiveSoonest(a).localeCompare(
          effectiveSoonest(b),
        );
        if (soonestDiff !== 0) return soonestDiff;
        return compareSiteNames(a.site, b.site, isMultiCampground);
      }
      case "name":
        return compareSiteNames(a.site, b.site, isMultiCampground);
      case "soonest":
      default: {
        const soonestDiff = effectiveSoonest(a).localeCompare(
          effectiveSoonest(b),
        );
        if (soonestDiff !== 0) return soonestDiff;
        const longestDiff = effectiveLongest(b) - effectiveLongest(a);
        if (longestDiff !== 0) return longestDiff;
        return compareSiteNames(a.site, b.site, isMultiCampground);
      }
    }
  });
}

export function toMonthRef(isoDate: string): MonthRef {
  const date = parseIsoDate(isoDate);
  return { year: date.getFullYear(), month: date.getMonth() };
}

export function compareMonths(a: MonthRef, b: MonthRef): number {
  return a.year !== b.year ? a.year - b.year : a.month - b.month;
}

export function shiftMonth(ref: MonthRef, delta: number): MonthRef {
  const d = new Date(ref.year, ref.month + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() };
}

export function clampMonth(
  ref: MonthRef,
  min: MonthRef,
  max: MonthRef,
): MonthRef {
  if (compareMonths(ref, min) < 0) return min;
  if (compareMonths(ref, max) > 0) return max;
  return ref;
}

/** Open on the month of the soonest qualifying opening, falling back to scan start when empty. */
export function getInitialCalendarMonth(
  sites: NormalizedFoundSite[],
  scanStartDate: string,
): MonthRef {
  let soonest: string | null = null;
  for (const site of sites) {
    if (soonest === null || site.soonestCheckIn < soonest) {
      soonest = site.soonestCheckIn;
    }
  }
  return toMonthRef(soonest ?? scanStartDate);
}

export function getCalendarMonthBounds(
  scanStartDate: string,
  scanEndDate: string,
): { min: MonthRef; max: MonthRef } {
  const min = toMonthRef(scanStartDate);
  const rawMax = toMonthRef(scanEndDate);
  const max = compareMonths(rawMax, min) < 0 ? min : rawMax;
  return { min, max };
}

/** Check whether an occupied night ISO string is a Friday or Saturday night. */
export function isWeekendNight(isoDate: string): boolean {
  const day = parseIsoDate(isoDate).getDay();
  return day === 5 || day === 6;
}

/** Build a Sun-Sat calendar grid for a month with search-filtered per-night site counts. */
export function buildCalendarMonth(
  year: number,
  month: number,
  scanStartDate: string,
  scanEndDate: string,
  sites: NormalizedFoundSite[],
  selection: DateSelection,
): CalendarMonth {
  const countsByDate = new Map<string, number>();
  for (const site of sites) {
    for (const night of site.availableNightSet) {
      countsByDate.set(night, (countsByDate.get(night) ?? 0) + 1);
    }
  }

  const firstOfMonth = new Date(year, month, 1);
  const firstDayIndex = firstOfMonth.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const totalCells = Math.ceil((firstDayIndex + daysInMonth) / 7) * 7;

  const days: CalendarDayCell[] = [];
  for (let cellIdx = 0; cellIdx < totalCells; cellIdx++) {
    const dayOffset = cellIdx - firstDayIndex + 1;
    const cellDate = new Date(year, month, dayOffset);
    const iso = toIsoDateString(cellDate);
    const isCurrentMonth =
      cellDate.getFullYear() === year && cellDate.getMonth() === month;
    const isInScanWindow = iso >= scanStartDate && iso < scanEndDate;
    const isCheckoutBoundary = iso === scanEndDate;
    const isSelectable =
      isCurrentMonth &&
      (isInScanWindow || (isCheckoutBoundary && selection?.end === null));

    days.push({
      date: iso,
      dayNumber: cellDate.getDate(),
      isCurrentMonth,
      isInScanWindow,
      isCheckoutBoundary,
      isWeekendNight: isWeekendNight(iso),
      availableSiteCount: isInScanWindow ? (countsByDate.get(iso) ?? 0) : 0,
      isSelectable,
    });
  }

  const label = firstOfMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return { year, month, label, days };
}

/** Build a bounded consecutive occupied-night window for the Sites x Dates Grid view. */
export function buildGridWindow(
  scanStartDate: string,
  scanEndDate: string,
  anchorDate: string | null,
  windowDays = GRID_WINDOW_DAYS,
): GridWindow {
  const totalNights = daysBetween(scanStartDate, scanEndDate);
  if (totalNights <= 0) {
    return {
      dates: [],
      startDate: scanStartDate,
      endDate: scanStartDate,
      canPrev: false,
      canNext: false,
    };
  }

  const count = Math.min(totalNights, Math.max(1, windowDays));
  const lastOccupiedNight = addDays(scanEndDate, -1);
  const maxStart = addDays(scanEndDate, -count);

  let start = anchorDate ?? scanStartDate;
  if (start < scanStartDate) start = scanStartDate;
  if (start > maxStart) start = maxStart;

  const dates: string[] = [];
  for (let i = 0; i < count; i++) {
    dates.push(addDays(start, i));
  }
  const endDate = dates[dates.length - 1] ?? lastOccupiedNight;

  return {
    dates,
    startDate: start,
    endDate,
    canPrev: start > scanStartDate,
    canNext: endDate < lastOccupiedNight,
  };
}

/** Format compact stay dates (e.g., "Thu, Jul 1"); includes year when crossing New Year's Day. */
export function formatStayDate(iso: string, includeYear: boolean): string {
  return parseIsoDate(iso).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    ...(includeYear ? { year: "numeric" } : {}),
  });
}

/** Human-readable summary for the active calendar date filter pill. */
export function formatDateSelectionSummary(
  selection: NonNullable<DateSelection>,
  includeYear = false,
): string {
  if (selection.end === null) {
    return `Night of ${formatStayDate(selection.start, includeYear)}`;
  }
  const showYear =
    includeYear || selection.start.slice(0, 4) !== selection.end.slice(0, 4);
  const nights = daysBetween(selection.start, selection.end);
  return `${formatStayDate(selection.start, showYear)} → ${formatStayDate(selection.end, showYear)} (${nights} night${nights !== 1 ? "s" : ""})`;
}
