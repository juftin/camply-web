import { useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  buildCalendarMonth,
  compareMonths,
  formatDateSelectionSummary,
  formatStayDate,
  getCalendarMonthBounds,
  shiftMonth,
  type DateSelection,
  type MonthRef,
  type NormalizedFoundSite,
} from "@/lib/availability";
import { cn } from "@/lib/utils";

const WEEKDAY_HEADERS = [
  { label: "Su", isWeekendNight: false },
  { label: "Mo", isWeekendNight: false },
  { label: "Tu", isWeekendNight: false },
  { label: "We", isWeekendNight: false },
  { label: "Th", isWeekendNight: false },
  { label: "Fr", isWeekendNight: true },
  { label: "Sa", isWeekendNight: true },
];

export interface AvailabilityCalendarProps {
  scanStartDate: string;
  scanEndDate: string;
  sites: NormalizedFoundSite[];
  visibleMonth: MonthRef;
  onVisibleMonthChange: (next: MonthRef) => void;
  selection: DateSelection;
  onSelectDate: (isoDate: string) => void;
  onClearSelection: () => void;
}

/** Interactive availability calendar highlighting open nights, counts, and weekend cues. */
export function AvailabilityCalendar({
  scanStartDate,
  scanEndDate,
  sites,
  visibleMonth,
  onVisibleMonthChange,
  selection,
  onSelectDate,
  onClearSelection,
}: AvailabilityCalendarProps) {
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  const bounds = useMemo(
    () => getCalendarMonthBounds(scanStartDate, scanEndDate),
    [scanStartDate, scanEndDate],
  );

  const calendar = useMemo(
    () =>
      buildCalendarMonth(
        visibleMonth.year,
        visibleMonth.month,
        scanStartDate,
        scanEndDate,
        sites,
        selection,
      ),
    [
      visibleMonth.year,
      visibleMonth.month,
      scanStartDate,
      scanEndDate,
      sites,
      selection,
    ],
  );

  const canPrev = compareMonths(visibleMonth, bounds.min) > 0;
  const canNext = compareMonths(visibleMonth, bounds.max) < 0;

  const previewRange = useMemo(() => {
    if (!selection) return null;
    if (selection.end) {
      return { start: selection.start, end: selection.end };
    }
    if (hoveredDate && hoveredDate !== selection.start) {
      return hoveredDate > selection.start
        ? { start: selection.start, end: hoveredDate }
        : { start: hoveredDate, end: selection.start };
    }
    return null;
  }, [selection, hoveredDate]);

  return (
    <div
      role="region"
      aria-label="Availability calendar"
      className="rounded-lg border bg-muted/20 p-3.5"
    >
      {/* Month header & bounded nav */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label="Previous month"
          disabled={!canPrev}
          onClick={() => onVisibleMonthChange(shiftMonth(visibleMonth, -1))}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-1.5 text-sm font-semibold">
          <CalendarDays
            aria-hidden="true"
            className="h-4 w-4 text-muted-foreground"
          />
          <span>{calendar.label}</span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label="Next month"
          disabled={!canNext}
          onClick={() => onVisibleMonthChange(shiftMonth(visibleMonth, 1))}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Day-of-week header */}
      <div className="mb-1 grid grid-cols-7 text-center text-[11px] font-semibold uppercase tracking-wide">
        {WEEKDAY_HEADERS.map((day) => (
          <div
            key={day.label}
            className={cn(
              "py-1",
              day.isWeekendNight
                ? "text-amber-700 dark:text-amber-400"
                : "text-muted-foreground",
            )}
          >
            {day.label}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div
        className="grid grid-cols-7 gap-1"
        onMouseLeave={() => setHoveredDate(null)}
      >
        {calendar.days.map((cell) => {
          if (!cell.isCurrentMonth) {
            return (
              <div
                key={cell.date}
                aria-hidden="true"
                className="flex h-11 items-center justify-center text-xs text-muted-foreground/30 select-none"
              >
                {cell.dayNumber}
              </div>
            );
          }

          const isSelectedStart = selection?.start === cell.date;
          const isSelectedEnd = selection?.end === cell.date;
          const isEndpoint = isSelectedStart || isSelectedEnd;
          const isInRange = Boolean(
            previewRange &&
            cell.date > previewRange.start &&
            cell.date < previewRange.end,
          );
          const isPreviewEnd = Boolean(
            selection?.end === null &&
            hoveredDate === cell.date &&
            hoveredDate !== selection.start,
          );
          const hasOpenings = cell.availableSiteCount > 0;

          const dateLabel = formatStayDate(cell.date, true);
          let availabilityText: string;
          if (cell.isCheckoutBoundary) {
            availabilityText = "check-out boundary";
          } else if (!cell.isInScanWindow) {
            availabilityText = "outside scan dates";
          } else if (hasOpenings) {
            availabilityText = `${cell.availableSiteCount} site${cell.availableSiteCount !== 1 ? "s" : ""} available`;
          } else {
            availabilityText = "no openings";
          }

          return (
            <button
              key={cell.date}
              type="button"
              disabled={!cell.isSelectable}
              aria-pressed={isEndpoint}
              aria-label={`${dateLabel} — ${availabilityText}`}
              onClick={() => onSelectDate(cell.date)}
              onMouseEnter={() => {
                if (cell.isSelectable) setHoveredDate(cell.date);
              }}
              onFocus={() => {
                if (cell.isSelectable) setHoveredDate(cell.date);
              }}
              className={cn(
                "flex h-11 flex-col items-center justify-center rounded-md border text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                !cell.isSelectable &&
                  "cursor-not-allowed border-transparent text-muted-foreground/35",
                cell.isSelectable &&
                  !isEndpoint &&
                  !isInRange &&
                  !isPreviewEnd &&
                  hasOpenings &&
                  "border-emerald-200 bg-emerald-50 text-emerald-950 hover:bg-emerald-100 dark:border-emerald-800/70 dark:bg-emerald-950/50 dark:text-emerald-100 dark:hover:bg-emerald-900/60",
                cell.isSelectable &&
                  !isEndpoint &&
                  !isInRange &&
                  !isPreviewEnd &&
                  !hasOpenings &&
                  (cell.isWeekendNight
                    ? "border-amber-200/60 bg-amber-50/40 text-muted-foreground hover:bg-muted/70 dark:border-amber-900/40 dark:bg-amber-950/20"
                    : "border-transparent bg-background/60 text-muted-foreground hover:bg-muted/70"),
                (isInRange || isPreviewEnd) &&
                  !isEndpoint &&
                  "border-primary/30 bg-primary/15 text-primary font-medium",
                isEndpoint &&
                  "border-primary bg-primary text-primary-foreground font-semibold shadow-sm hover:bg-primary/90",
              )}
            >
              <span className="leading-tight">{cell.dayNumber}</span>
              {hasOpenings && cell.isInScanWindow && (
                <span
                  aria-hidden="true"
                  className={cn(
                    "mt-0.5 text-[10px] font-semibold leading-none",
                    isEndpoint
                      ? "text-primary-foreground/90"
                      : "text-emerald-700 dark:text-emerald-300",
                  )}
                >
                  {cell.availableSiteCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Active selection bar or helpful hint + legend */}
      <div className="mt-3 space-y-2 border-t pt-3">
        {selection ? (
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs font-medium text-foreground">
                {formatDateSelectionSummary(selection)}
              </p>
              {selection.end === null && (
                <p className="text-[11px] text-muted-foreground">
                  Click another date for check-out, or click again to clear.
                </p>
              )}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onClearSelection}
            >
              <X aria-hidden="true" className="mr-1 h-3 w-3" />
              Clear dates
            </Button>
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground">
            Click a night to filter, or pick check-in and check-out dates.
          </p>
        )}

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 rounded-sm border border-emerald-300 bg-emerald-100 dark:border-emerald-700 dark:bg-emerald-950"
            />
            Open night (site count)
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
    </div>
  );
}
