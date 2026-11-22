import { useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  Grid3X3,
  LayoutList,
  Search,
  Tent,
  X,
} from "lucide-react";
import { useLocation } from "react-router-dom";
import { AvailabilityCalendar } from "@/components/found-campsites/AvailabilityCalendar";
import { AvailabilityGrid } from "@/components/found-campsites/AvailabilityGrid";
import { CampsiteCardList } from "@/components/found-campsites/CampsiteCardList";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  SITES_PER_PAGE,
  applyCalendarDayClick,
  clampMonth,
  filterAndSortSites,
  filterSitesBySearch,
  formatDateSelectionSummary,
  getCalendarMonthBounds,
  getInitialCalendarMonth,
  normalizeFoundSites,
  type DateSelection,
  type FoundSortMode,
  type FoundViewMode,
  type MonthRef,
} from "@/lib/availability";
import type { ScanDetailResponse } from "@/lib/structs";
import { cn } from "@/lib/utils";

export interface FoundCampsitesProps {
  scan: ScanDetailResponse;
}

/** Visual-first campsite results with interactive calendar, deduplicated cards, and grid view. */
export const FoundCampsites = ({ scan }: FoundCampsitesProps) => {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<FoundSortMode>("soonest");
  const [viewMode, setViewMode] = useState<FoundViewMode>("cards");
  const [dateSelection, setDateSelection] = useState<DateSelection>(null);
  const [page, setPage] = useState(0);

  const section = useRef<HTMLElement>(null);
  const { hash } = useLocation();
  useEffect(() => {
    if (hash === "#results") {
      section.current?.scrollIntoView?.({ block: "start" });
    }
  }, [hash]);

  const allSites = useMemo(
    () => normalizeFoundSites(scan.results ?? [], scan.min_stay_length),
    [scan.results, scan.min_stay_length],
  );

  const isMultiCampground = useMemo(() => {
    if (scan.destination_type === "recreation_area") return true;
    const ids = new Set(allSites.map((s) => s.campgroundId).filter(Boolean));
    return ids.size > 1;
  }, [scan.destination_type, allSites]);

  const monthBounds = useMemo(
    () => getCalendarMonthBounds(scan.start_date, scan.end_date),
    [scan.start_date, scan.end_date],
  );

  const [visibleMonth, setVisibleMonth] = useState<MonthRef>(() =>
    getInitialCalendarMonth(allSites, scan.start_date),
  );
  const [hasUserNavigatedMonth, setHasUserNavigatedMonth] = useState(false);

  // Anchor to the soonest opening month on first results arrival unless the user already navigated.
  useEffect(() => {
    if (!hasUserNavigatedMonth && allSites.length > 0) {
      setVisibleMonth(getInitialCalendarMonth(allSites, scan.start_date));
    }
  }, [allSites, hasUserNavigatedMonth, scan.start_date]);

  // Clamp visible month and clear out-of-window date selection if scan dates are edited.
  useEffect(() => {
    setVisibleMonth((previous) =>
      clampMonth(previous, monthBounds.min, monthBounds.max),
    );
    setDateSelection((previous) => {
      if (!previous) return null;
      const startValid =
        previous.start >= scan.start_date && previous.start < scan.end_date;
      const endValid =
        previous.end === null ||
        (previous.end > previous.start && previous.end <= scan.end_date);
      return startValid && endValid ? previous : null;
    });
  }, [monthBounds.min, monthBounds.max, scan.start_date, scan.end_date]);

  const soonestOpeningDate = useMemo(() => {
    let soonest: string | null = null;
    for (const s of allSites) {
      if (soonest === null || s.soonestCheckIn < soonest) {
        soonest = s.soonestCheckIn;
      }
    }
    return soonest ?? scan.start_date;
  }, [allSites, scan.start_date]);

  const [gridStartDate, setGridStartDate] = useState<string>(
    () => soonestOpeningDate,
  );
  const [hasUserNavigatedGrid, setHasUserNavigatedGrid] = useState(false);

  // Re-anchor grid start to the soonest opening when initial results arrive or scan dates shift.
  useEffect(() => {
    if (!hasUserNavigatedGrid && !dateSelection) {
      setGridStartDate(soonestOpeningDate);
    } else if (
      gridStartDate < scan.start_date ||
      gridStartDate >= scan.end_date
    ) {
      setHasUserNavigatedGrid(false);
      setGridStartDate(soonestOpeningDate);
    }
  }, [
    soonestOpeningDate,
    hasUserNavigatedGrid,
    dateSelection,
    gridStartDate,
    scan.start_date,
    scan.end_date,
  ]);

  // Search-filtered sites drive calendar day counts so search immediately highlights matching dates.
  const searchFilteredSites = useMemo(
    () => filterSitesBySearch(allSites, query),
    [allSites, query],
  );

  const visibleItems = useMemo(
    () =>
      filterAndSortSites(
        allSites,
        query,
        dateSelection,
        sort,
        isMultiCampground,
      ),
    [allSites, query, dateSelection, sort, isMultiCampground],
  );

  const openingCount = useMemo(
    () =>
      visibleItems.reduce((sum, entry) => sum + entry.matchingStays.length, 0),
    [visibleItems],
  );

  const pageCount = Math.max(
    1,
    Math.ceil(visibleItems.length / SITES_PER_PAGE),
  );
  const currentPage = Math.min(page, pageCount - 1);
  const pagedItems = useMemo(
    () =>
      visibleItems.slice(
        currentPage * SITES_PER_PAGE,
        (currentPage + 1) * SITES_PER_PAGE,
      ),
    [visibleItems, currentPage],
  );

  useEffect(() => {
    setPage((previous) => Math.min(previous, pageCount - 1));
  }, [pageCount]);

  const handleSelectCalendarDate = (isoDate: string) => {
    const next = applyCalendarDayClick(
      dateSelection,
      isoDate,
      scan.start_date,
      scan.end_date,
    );
    setDateSelection(next);
    setPage(0);
    if (next) {
      setGridStartDate(next.start);
    }
  };

  const handleClearDates = () => {
    setDateSelection(null);
    setPage(0);
  };

  const handleQueryChange = (nextQuery: string) => {
    setQuery(nextQuery);
    setPage(0);
  };

  const handleSortChange = (nextSort: FoundSortMode) => {
    setSort(nextSort);
    setPage(0);
  };

  const handleClearAllFilters = () => {
    setQuery("");
    setDateSelection(null);
    setPage(0);
  };

  const handleMonthChange = (next: MonthRef) => {
    setHasUserNavigatedMonth(true);
    setVisibleMonth(clampMonth(next, monthBounds.min, monthBounds.max));
  };

  const handleGridWindowStartChange = (nextStart: string) => {
    setHasUserNavigatedGrid(true);
    setGridStartDate(nextStart);
  };

  const handleViewChange = (nextMode: FoundViewMode) => {
    setViewMode(nextMode);
    if (nextMode === "grid" && dateSelection) {
      setGridStartDate(dateSelection.start);
    }
  };

  const includeYearByDefault =
    scan.start_date.slice(0, 4) !== scan.end_date.slice(0, 4);
  const hasSearch = query.trim().length > 0;
  const hasDateFilter = dateSelection !== null;
  const isPartialAreaEmpty =
    scan.destination_type === "recreation_area" &&
    scan.coverage_status !== "complete";

  return (
    <section
      id="results"
      ref={section}
      aria-labelledby="found-campsites-heading"
      className="scroll-mt-24"
    >
      <Card className="overflow-hidden">
        <CardHeader className="space-y-3 border-b pb-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle id="found-campsites-heading" className="text-xl">
              Found campsites
            </CardTitle>
            <p role="status" className="text-sm text-muted-foreground">
              {visibleItems.length} site{visibleItems.length !== 1 ? "s" : ""} ·{" "}
              {openingCount} opening{openingCount !== 1 ? "s" : ""}
            </p>
          </div>

          {!scan.is_active && allSites.length > 0 && (
            <p className="rounded-md border border-amber-500/30 bg-amber-50/70 px-3 py-2 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
              This scan is paused; availability is not being refreshed.
            </p>
          )}

          {allSites.length > 0 && (
            <div className="flex flex-col gap-3 pt-1 md:flex-row md:items-center md:justify-between">
              <div className="relative w-full md:max-w-xs">
                <Search
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  type="search"
                  aria-label="Search found campsites"
                  placeholder={
                    isMultiCampground
                      ? "Search sites, types, or campgrounds"
                      : "Search sites or campsite types"
                  }
                  value={query}
                  onChange={(event) => handleQueryChange(event.target.value)}
                  className="pl-9"
                />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="sr-only sm:not-sr-only">Sort</span>
                  <span className="relative">
                    <select
                      aria-label="Sort campsites"
                      value={sort}
                      onChange={(event) =>
                        handleSortChange(event.target.value as FoundSortMode)
                      }
                      className="h-9 w-44 appearance-none rounded-md border bg-background pl-3 pr-8 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="soonest">Soonest opening</option>
                      <option value="longest">Longest stay</option>
                      <option value="most_nights">Most available nights</option>
                      <option value="name">Site name</option>
                    </select>
                    <ChevronDown
                      aria-hidden="true"
                      className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    />
                  </span>
                </label>

                <div
                  role="group"
                  aria-label="Results view"
                  className="inline-flex rounded-md border bg-muted/40 p-0.5"
                >
                  <button
                    type="button"
                    aria-pressed={viewMode === "cards"}
                    onClick={() => handleViewChange("cards")}
                    className={cn(
                      "inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      viewMode === "cards"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <LayoutList aria-hidden="true" className="h-3.5 w-3.5" />
                    Cards
                  </button>
                  <button
                    type="button"
                    aria-pressed={viewMode === "grid"}
                    onClick={() => handleViewChange("grid")}
                    className={cn(
                      "inline-flex h-8 items-center gap-1.5 rounded-sm px-2.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      viewMode === "grid"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Grid3X3 aria-hidden="true" className="h-3.5 w-3.5" />
                    Grid
                  </button>
                </div>
              </div>
            </div>
          )}
        </CardHeader>

        <CardContent className="p-4 sm:p-6">
          {allSites.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center">
              <Tent
                aria-hidden="true"
                className="mx-auto mb-3 h-8 w-8 text-muted-foreground"
              />
              <p className="font-medium">
                {!scan.last_checked_at
                  ? "Waiting for the first check"
                  : isPartialAreaEmpty
                    ? "No matching campsites in checked campgrounds yet"
                    : "No matching campsites right now"}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {!scan.is_active
                  ? "This scan is paused. Resume it from your dashboard to check for new openings."
                  : isPartialAreaEmpty && scan.last_checked_at
                    ? "Some campgrounds in this area are still pending or failed; Camply will notify you when openings match."
                    : "Camply will notify you when new openings match your scan."}
              </p>
            </div>
          ) : viewMode === "cards" ? (
            <div className="grid gap-6 lg:grid-cols-[310px_minmax(0,1fr)] lg:items-start">
              <div className="lg:sticky lg:top-20">
                <AvailabilityCalendar
                  scanStartDate={scan.start_date}
                  scanEndDate={scan.end_date}
                  sites={searchFilteredSites}
                  visibleMonth={visibleMonth}
                  onVisibleMonthChange={handleMonthChange}
                  selection={dateSelection}
                  onSelectDate={handleSelectCalendarDate}
                  onClearSelection={handleClearDates}
                />
              </div>

              <div className="min-w-0">
                {visibleItems.length > 0 ? (
                  <CampsiteCardList
                    items={pagedItems}
                    totalMatchingSites={visibleItems.length}
                    page={currentPage}
                    pageCount={pageCount}
                    onPageChange={setPage}
                    isMultiCampground={isMultiCampground}
                    scanCampgroundName={scan.campground_name}
                    hasDateSelection={hasDateFilter}
                    includeYearByDefault={includeYearByDefault}
                  />
                ) : (
                  <div className="rounded-lg border border-dashed p-8 text-center">
                    <p className="font-medium">
                      {hasSearch && hasDateFilter
                        ? "No campsites match your search and selected dates."
                        : hasDateFilter
                          ? "No campsites are continuously available for the selected dates."
                          : "No campsites match your search."}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                      {hasSearch && hasDateFilter ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleClearAllFilters}
                        >
                          Clear filters
                        </Button>
                      ) : hasDateFilter ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleClearDates}
                        >
                          Clear dates
                        </Button>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleQueryChange("")}
                        >
                          Clear search
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {dateSelection && (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs">
                  <span>
                    Filtered dates:{" "}
                    <strong className="font-semibold text-foreground">
                      {formatDateSelectionSummary(dateSelection)}
                    </strong>
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={handleClearDates}
                  >
                    <X aria-hidden="true" className="mr-1 h-3 w-3" />
                    Clear dates
                  </Button>
                </div>
              )}

              {visibleItems.length > 0 ? (
                <AvailabilityGrid
                  scanStartDate={scan.start_date}
                  scanEndDate={scan.end_date}
                  items={pagedItems}
                  totalMatchingSites={visibleItems.length}
                  page={currentPage}
                  pageCount={pageCount}
                  onPageChange={setPage}
                  isMultiCampground={isMultiCampground}
                  dateSelection={dateSelection}
                  windowStartDate={gridStartDate}
                  onWindowStartChange={handleGridWindowStartChange}
                  includeYearByDefault={includeYearByDefault}
                />
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center">
                  <p className="font-medium">
                    {hasSearch && hasDateFilter
                      ? "No campsites match your search and selected dates."
                      : hasDateFilter
                        ? "No campsites are continuously available for the selected dates."
                        : "No campsites match your search."}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                    {hasSearch && hasDateFilter ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleClearAllFilters}
                      >
                        Clear filters
                      </Button>
                    ) : hasDateFilter ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleClearDates}
                      >
                        Clear dates
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => handleQueryChange("")}
                      >
                        Clear search
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>

        <p className="border-t bg-muted/20 px-4 py-3 text-xs text-muted-foreground sm:px-6">
          Dates show check-in → check-out. Availability can change quickly;
          confirm stay rules and vehicle length limits with the booking provider
          before reserving.
        </p>
      </Card>
    </section>
  );
};
