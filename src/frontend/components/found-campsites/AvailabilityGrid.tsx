import { useEffect, useMemo, useState } from "react";
import {
  Accessibility,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  X,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CampsitePagination,
  SiteCapabilities,
} from "@/components/found-campsites/CampsiteCardList";
import {
  GRID_WINDOW_DAYS,
  buildGridWindow,
  formatStayDate,
  isWeekendNight,
  stayKey,
  type AvailableStay,
  type DateSelection,
  type FilteredFoundSite,
  type SelectedGridStay,
} from "@/lib/availability";
import { addDays, cn, formatRelativeTime, parseIsoDate } from "@/lib/utils";

export interface AvailabilityGridProps {
  scanStartDate: string;
  scanEndDate: string;
  items: FilteredFoundSite[];
  totalMatchingSites: number;
  page: number;
  pageCount: number;
  onPageChange: (nextPage: number) => void;
  isMultiCampground: boolean;
  dateSelection: DateSelection;
  windowStartDate: string;
  onWindowStartChange: (nextStart: string) => void;
  includeYearByDefault: boolean;
}

function formatWindowRange(startIso: string, endIso: string): string {
  if (!startIso) return "";
  const start = parseIsoDate(startIso);
  const end = parseIsoDate(endIso);
  const sameYear = start.getFullYear() === end.getFullYear();
  const startStr = start.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    ...(sameYear ? {} : { year: "numeric" }),
  });
  const endStr = end.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return startIso === endIso ? endStr : `${startStr} – ${endStr}`;
}

/** Sites x Dates availability matrix with sticky campsite labels and inline stay inspector. */
export function AvailabilityGrid({
  scanStartDate,
  scanEndDate,
  items,
  totalMatchingSites,
  page,
  pageCount,
  onPageChange,
  isMultiCampground,
  dateSelection,
  windowStartDate,
  onWindowStartChange,
  includeYearByDefault,
}: AvailabilityGridProps) {
  const [selectedStay, setSelectedStay] = useState<SelectedGridStay>(null);

  const gridWindow = useMemo(
    () =>
      buildGridWindow(
        scanStartDate,
        scanEndDate,
        windowStartDate,
        GRID_WINDOW_DAYS,
      ),
    [scanStartDate, scanEndDate, windowStartDate],
  );

  // Resolve inspected stay against the currently visible items; clears automatically if removed.
  const inspected = useMemo(() => {
    if (!selectedStay) return null;
    const entry = items.find((item) => item.site.key === selectedStay.siteKey);
    if (!entry) return null;
    const stay = entry.site.stays.find(
      (s) =>
        s.start === selectedStay.stayStart && s.end === selectedStay.stayEnd,
    );
    if (!stay) return null;
    return { site: entry.site, stay };
  }, [items, selectedStay]);

  // Keep state synced when inspected item disappears.
  useEffect(() => {
    if (selectedStay && !inspected) {
      setSelectedStay(null);
    }
  }, [selectedStay, inspected]);

  // Dismiss inline stay inspector on Escape.
  useEffect(() => {
    if (!inspected) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedStay(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [inspected]);

  const handleToggleCell = (siteKey: string, stay: AvailableStay) => {
    setSelectedStay((previous) =>
      previous &&
      previous.siteKey === siteKey &&
      previous.stayStart === stay.start &&
      previous.stayEnd === stay.end
        ? null
        : { siteKey, stayStart: stay.start, stayEnd: stay.end },
    );
  };

  return (
    <div className="space-y-3">
      {/* Window navigation & legend */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-label="Previous dates"
            disabled={!gridWindow.canPrev}
            onClick={() =>
              onWindowStartChange(
                addDays(gridWindow.startDate, -GRID_WINDOW_DAYS),
              )
            }
          >
            <ChevronLeft aria-hidden="true" className="h-4 w-4" />
          </Button>
          <span className="min-w-[10rem] text-center text-xs font-semibold sm:text-sm">
            {formatWindowRange(gridWindow.startDate, gridWindow.endDate)}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-label="Next dates"
            disabled={!gridWindow.canNext}
            onClick={() =>
              onWindowStartChange(
                addDays(gridWindow.startDate, GRID_WINDOW_DAYS),
              )
            }
          >
            <ChevronRight aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-sm border border-emerald-500/50 bg-emerald-500/25"
            />
            Open night (click to inspect)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-sm border border-amber-300/80 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40"
            />
            Fri/Sat night
          </span>
        </div>
      </div>

      {/* Inline stay inspector */}
      {inspected && (
        <div
          role="region"
          aria-label="Selected stay details"
          className="rounded-lg border border-primary/40 bg-primary/5 p-4"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                {inspected.site.campgroundName && isMultiCampground && (
                  <span className="text-xs font-medium text-muted-foreground">
                    {inspected.site.campgroundName} ·
                  </span>
                )}
                <h3 className="text-sm font-semibold">
                  {inspected.site.displayName}
                </h3>
                {inspected.site.isStale && (
                  <Badge variant="warning" className="gap-1 text-[11px]">
                    <AlertTriangle aria-hidden="true" className="h-3 w-3" />
                    Stale
                    {inspected.site.lastCheckedAt
                      ? ` · ${formatRelativeTime(inspected.site.lastCheckedAt)}`
                      : ""}
                  </Badge>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-background px-2.5 py-1 font-medium text-foreground">
                  <time dateTime={inspected.stay.start}>
                    {formatStayDate(
                      inspected.stay.start,
                      includeYearByDefault ||
                        inspected.stay.start.slice(0, 4) !==
                          inspected.stay.end.slice(0, 4),
                    )}
                  </time>
                  <span aria-hidden="true" className="text-muted-foreground">
                    →
                  </span>
                  <time dateTime={inspected.stay.end}>
                    {formatStayDate(
                      inspected.stay.end,
                      includeYearByDefault ||
                        inspected.stay.start.slice(0, 4) !==
                          inspected.stay.end.slice(0, 4),
                    )}
                  </time>
                  <Badge variant="secondary" className="ml-1 text-[10px]">
                    {inspected.stay.nights} night
                    {inspected.stay.nights !== 1 ? "s" : ""}
                  </Badge>
                </span>
              </div>

              <SiteCapabilities site={inspected.site} />
            </div>

            <div className="flex items-center gap-2 self-start">
              {inspected.site.bookingUrl && (
                <Button asChild size="sm" className="gap-1.5">
                  <a
                    href={inspected.site.bookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`View ${inspected.site.displayName} on provider website${inspected.site.campgroundName ? ` (${inspected.site.campgroundName})` : ""}`}
                  >
                    View on provider
                    <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
                  </a>
                </Button>
              )}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Close stay details"
                onClick={() => setSelectedStay(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Scrollable matrix container (keeps document width strictly within viewport) */}
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="border-b bg-muted/40">
              <th
                scope="col"
                className="sticky left-0 z-10 min-w-[155px] max-w-[190px] border-r bg-muted/95 px-3 py-2.5 text-left font-semibold text-foreground backdrop-blur sm:min-w-[205px]"
              >
                Campsite
              </th>
              {gridWindow.dates.map((date, idx) => {
                const parsed = parseIsoDate(date);
                const weekday = parsed.toLocaleDateString("en-US", {
                  weekday: "short",
                });
                const monthShort = parsed.toLocaleDateString("en-US", {
                  month: "short",
                });
                const showMonth =
                  idx === 0 ||
                  date.slice(0, 7) !== gridWindow.dates[idx - 1].slice(0, 7);
                const weekend = isWeekendNight(date);
                const inActiveDateFilter = Boolean(
                  dateSelection &&
                  (dateSelection.end === null
                    ? date === dateSelection.start
                    : date >= dateSelection.start && date < dateSelection.end),
                );

                return (
                  <th
                    key={date}
                    scope="col"
                    className={cn(
                      "min-w-[44px] px-1 py-2 text-center font-medium",
                      weekend && "bg-amber-50/70 dark:bg-amber-950/30",
                      inActiveDateFilter && "bg-primary/10 text-primary",
                    )}
                  >
                    <div className="text-[10px] font-normal text-muted-foreground">
                      {showMonth ? monthShort : "\u00A0"}
                    </div>
                    <div
                      className={cn(
                        "text-[10px] uppercase",
                        weekend
                          ? "font-semibold text-amber-700 dark:text-amber-400"
                          : "text-muted-foreground",
                      )}
                    >
                      {weekday.slice(0, 2)}
                    </div>
                    <div className="text-xs font-semibold">
                      {parsed.getDate()}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.map(({ site, matchingStayKeys }) => {
              const stayByDate = new Map<string, AvailableStay>();
              for (const stay of site.stays) {
                for (const d of stay.dates) {
                  stayByDate.set(d, stay);
                }
              }

              return (
                <tr key={site.key} className="hover:bg-muted/20">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-r bg-card px-3 py-2.5 text-left font-normal"
                  >
                    {isMultiCampground && site.campgroundName && (
                      <div className="truncate text-[11px] text-muted-foreground">
                        {site.campgroundName}
                      </div>
                    )}
                    <div className="flex items-center gap-1.5">
                      <span className="truncate font-semibold text-foreground">
                        {site.displayName}
                      </span>
                      {site.isStale && (
                        <AlertTriangle
                          aria-label="Stale observation"
                          className="h-3 w-3 shrink-0 text-amber-600 dark:text-amber-400"
                        />
                      )}
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                      {site.campsiteType && (
                        <span className="truncate">{site.campsiteType}</span>
                      )}
                      {site.isElectric && (
                        <Zap
                          aria-label="Electric hookup"
                          className="h-3 w-3 shrink-0"
                        />
                      )}
                      {site.isAccessible && (
                        <Accessibility
                          aria-label="Accessible"
                          className="h-3 w-3 shrink-0"
                        />
                      )}
                      {site.maxVehicleLength != null && (
                        <span>{site.maxVehicleLength} ft</span>
                      )}
                    </div>
                  </th>

                  {gridWindow.dates.map((date) => {
                    const stay = stayByDate.get(date);
                    const weekend = isWeekendNight(date);

                    if (!stay) {
                      return (
                        <td
                          key={date}
                          className={cn(
                            "p-1 text-center",
                            weekend && "bg-amber-50/40 dark:bg-amber-950/15",
                          )}
                        >
                          <span
                            aria-hidden="true"
                            className="inline-block h-7 w-full rounded bg-muted/35"
                          />
                        </td>
                      );
                    }

                    const isSelectedCell = Boolean(
                      inspected &&
                      inspected.site.key === site.key &&
                      inspected.stay.start === stay.start &&
                      inspected.stay.end === stay.end,
                    );
                    const isMatchingFilter = Boolean(
                      dateSelection && matchingStayKeys.has(stayKey(stay)),
                    );
                    const includeYear =
                      includeYearByDefault ||
                      stay.start.slice(0, 4) !== stay.end.slice(0, 4);

                    return (
                      <td
                        key={date}
                        className={cn(
                          "p-1 text-center",
                          weekend && "bg-amber-50/40 dark:bg-amber-950/15",
                        )}
                      >
                        <button
                          type="button"
                          aria-pressed={isSelectedCell}
                          aria-label={`${site.displayName}, ${formatStayDate(date, true)}, available ${formatStayDate(stay.start, includeYear)} to ${formatStayDate(stay.end, includeYear)} (${stay.nights} night${stay.nights !== 1 ? "s" : ""})`}
                          onClick={() => handleToggleCell(site.key, stay)}
                          className={cn(
                            "flex h-7 w-full items-center justify-center rounded border text-[10px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                            isSelectedCell
                              ? "border-primary bg-primary text-primary-foreground shadow-sm"
                              : isMatchingFilter
                                ? "border-primary/60 bg-emerald-500/30 text-emerald-950 ring-1 ring-primary/40 hover:bg-emerald-500/45 dark:text-emerald-100"
                                : "border-emerald-500/40 bg-emerald-500/20 text-emerald-900 hover:bg-emerald-500/35 dark:border-emerald-500/50 dark:bg-emerald-500/25 dark:text-emerald-100 dark:hover:bg-emerald-500/40",
                          )}
                        >
                          ✓
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <CampsitePagination
        page={page}
        pageCount={pageCount}
        totalMatchingSites={totalMatchingSites}
        onPageChange={onPageChange}
      />
    </div>
  );
}
