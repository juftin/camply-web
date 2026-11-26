import { useState, useEffect, useRef, useMemo, type ReactElement } from "react";
import { CalendarIcon, ChevronLeft, ChevronRight, X } from "lucide-react";

import {
  cn,
  addDays,
  daysBetween,
  formatDisplayDate,
  getTodayString,
  parseIsoDate,
  toIsoDateString,
  getUpcomingFriday,
} from "@/lib/utils";

export interface DatePickerProps {
  id?: string;
  name?: string;
  value?: string; // ISO date 'YYYY-MM-DD'
  onChange?: (date: string) => void;
  minDate?: string; // ISO date 'YYYY-MM-DD'
  maxDate?: string; // ISO date 'YYYY-MM-DD'
  defaultMonth?: string; // ISO date 'YYYY-MM-DD' (anchors view when value is empty)
  startDate?: string; // ISO date 'YYYY-MM-DD' (for check-out pickers)
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
  align?: "left" | "right";
  showPresets?: boolean;
}

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const DAYS_OF_WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export function DatePicker({
  id,
  name,
  value = "",
  onChange,
  minDate,
  maxDate,
  defaultMonth,
  startDate,
  placeholder = "Select date",
  disabled = false,
  error = false,
  className,
  align = "left",
  showPresets = true,
}: DatePickerProps): ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  // Compute view month & year based on value -> defaultMonth -> today
  const initialView = useMemo(() => {
    const anchor = value || defaultMonth || getTodayString();
    const d = parseIsoDate(anchor);
    return { year: d.getFullYear(), month: d.getMonth() };
  }, [value, defaultMonth]);

  const [viewState, setViewState] = useState(initialView);

  // Keep viewState updated when defaultMonth or value changes while unopened
  useEffect(() => {
    if (!isOpen) {
      const anchor = value || defaultMonth || getTodayString();
      const d = parseIsoDate(anchor);
      setViewState({ year: d.getFullYear(), month: d.getMonth() });
    }
  }, [value, defaultMonth, isOpen]);

  const containerRef = useRef<HTMLDivElement>(null);
  const calendarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && window.matchMedia?.("(max-width: 639.98px)")?.matches) {
      calendarRef.current?.scrollIntoView({ block: "nearest" });
    }
  }, [isOpen]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (e: Event) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setIsOpen(false);
        containerRef.current?.querySelector("button")?.focus();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    window.addEventListener("keydown", handleKeyDown, true);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      window.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [isOpen]);

  const todayStr = useMemo(() => getTodayString(), []);

  // Effective minDate: if startDate is provided, checkout cannot be <= startDate
  const effectiveMinDate = useMemo(() => {
    if (minDate) return minDate;
    if (startDate) return addDays(startDate, 1);
    return undefined;
  }, [minDate, startDate]);

  // Navigate months
  const handlePrevMonth = () => {
    setViewState((prev) => {
      if (prev.month === 0) {
        return { year: prev.year - 1, month: 11 };
      }
      return { year: prev.year, month: prev.month - 1 };
    });
  };

  const handleNextMonth = () => {
    setViewState((prev) => {
      if (prev.month === 11) {
        return { year: prev.year + 1, month: 0 };
      }
      return { year: prev.year, month: prev.month + 1 };
    });
  };

  const handleMonthSelect = (m: number) => {
    setViewState((prev) => ({ ...prev, month: m }));
  };

  const handleYearSelect = (y: number) => {
    setViewState((prev) => ({ ...prev, year: y }));
  };

  // Calendar cells computation
  const calendarDays = useMemo(() => {
    const { year, month } = viewState;
    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();

    const days: {
      dateStr: string;
      dayNumber: number;
      isCurrentMonth: boolean;
      isDisabled: boolean;
      isSelected: boolean;
      isToday: boolean;
      isStartDate: boolean;
      isInRange: boolean;
    }[] = [];

    // Leading days from previous month
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const dNum = prevMonthDays - i;
      const prevMonth = month === 0 ? 11 : month - 1;
      const prevYear = month === 0 ? year - 1 : year;
      const dateStr = toIsoDateString(new Date(prevYear, prevMonth, dNum));
      days.push({
        dateStr,
        dayNumber: dNum,
        isCurrentMonth: false,
        isDisabled: true,
        isSelected: false,
        isToday: dateStr === todayStr,
        isStartDate: dateStr === startDate,
        isInRange: false,
      });
    }

    // Days in current month
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = toIsoDateString(new Date(year, month, day));
      const isDisabled = Boolean(
        (effectiveMinDate && dateStr < effectiveMinDate) ||
        (maxDate && dateStr > maxDate),
      );
      const isSelected = dateStr === value;
      const isStart = Boolean(startDate && dateStr === startDate);

      // Check range preview
      let inRange = false;
      if (startDate) {
        const compareTarget = value || hoveredDate;
        if (
          compareTarget &&
          compareTarget > startDate &&
          dateStr > startDate &&
          dateStr < compareTarget
        ) {
          inRange = true;
        }
      }

      days.push({
        dateStr,
        dayNumber: day,
        isCurrentMonth: true,
        isDisabled,
        isSelected,
        isToday: dateStr === todayStr,
        isStartDate: isStart,
        isInRange: inRange,
      });
    }

    // Trailing days to complete 6 rows (42 cells)
    const remaining = 42 - days.length;
    for (let i = 1; i <= remaining; i++) {
      const nextMonth = month === 11 ? 0 : month + 1;
      const nextYear = month === 11 ? year + 1 : year;
      const dateStr = toIsoDateString(new Date(nextYear, nextMonth, i));
      days.push({
        dateStr,
        dayNumber: i,
        isCurrentMonth: false,
        isDisabled: true,
        isSelected: false,
        isToday: dateStr === todayStr,
        isStartDate: dateStr === startDate,
        isInRange: false,
      });
    }

    return days;
  }, [
    viewState,
    effectiveMinDate,
    maxDate,
    value,
    todayStr,
    startDate,
    hoveredDate,
  ]);

  const handleSelectDay = (dateStr: string) => {
    onChange?.(dateStr);
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange?.("");
    setIsOpen(false);
    containerRef.current?.querySelector("button")?.focus();
  };

  // Quick preset calculations
  const presets = useMemo(() => {
    if (!showPresets) return [];

    if (startDate) {
      // Check-out presets relative to start date
      return [
        { label: "1 night", date: addDays(startDate, 1) },
        { label: "2 nights", date: addDays(startDate, 2) },
        { label: "3 nights", date: addDays(startDate, 3) },
        { label: "7 nights", date: addDays(startDate, 7) },
      ];
    }

    // Check-in presets relative to today
    const tomorrow = addDays(todayStr, 1);
    const thisWeekend = getUpcomingFriday(todayStr);
    const nextWeekend = addDays(thisWeekend, 7);

    return [
      { label: "Today", date: todayStr },
      { label: "Tomorrow", date: tomorrow },
      { label: "This Weekend", date: thisWeekend },
      { label: "Next Weekend", date: nextWeekend },
    ];
  }, [showPresets, startDate, todayStr]);

  // Year options for jump dropdown: current year to +3 years
  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return [currentYear, currentYear + 1, currentYear + 2, currentYear + 3];
  }, []);

  // Display text for the button
  const formattedDisplay = value ? formatDisplayDate(value, true) : placeholder;

  // Active stay calculation for helper text in popover
  const previewStayNights = useMemo(() => {
    if (!startDate) return null;
    const target = hoveredDate || value;
    if (target && target > startDate) {
      return daysBetween(startDate, target);
    }
    return null;
  }, [startDate, hoveredDate, value]);

  return (
    <div className="relative inline-block w-full" ref={containerRef}>
      {/* Hidden input for form integration / test queries */}
      <input
        type="hidden"
        name={name}
        value={value}
        data-testid={id ? `${id}-hidden` : undefined}
      />

      <div className="relative">
        <button
          type="button"
          id={id}
          disabled={disabled}
          onClick={() => {
            if (!disabled) {
              setIsOpen((prev) => !prev);
            }
          }}
          aria-expanded={isOpen}
          aria-haspopup="dialog"
          className={cn(
            "flex h-11 sm:h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm text-left ring-offset-background transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            !value && "text-muted-foreground",
            value && !disabled && "pr-11 sm:pr-8",
            error && "border-destructive focus-visible:ring-destructive",
            className,
          )}
        >
          <div className="flex items-center gap-2.5 overflow-hidden truncate">
            <CalendarIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span
              className={cn("truncate font-medium", !value && "font-normal")}
            >
              {formattedDisplay}
            </span>
          </div>
        </button>
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:right-2 sm:inset-y-auto sm:top-1/2 sm:h-6 sm:w-6 sm:-translate-y-1/2"
            aria-label="Clear date"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Calendar Popover */}
      {isOpen && (
        <div
          ref={calendarRef}
          role="dialog"
          aria-label="Choose a date"
          className={cn(
            "relative sm:absolute sm:top-full z-50 mt-1.5 w-[min(calc(100vw-3rem),316px)] max-w-full sm:max-w-none rounded-lg border bg-popover p-2 sm:p-3 text-popover-foreground shadow-xl motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95",
            align === "right" ? "sm:right-0" : "sm:left-0",
          )}
        >
          {/* Header Month / Year controls */}
          <div className="flex items-center justify-between gap-1 pb-2 border-b">
            <button
              type="button"
              onClick={handlePrevMonth}
              className="h-10 w-10 shrink-0 sm:h-9 sm:w-9 inline-flex items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
              aria-label="Previous month"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <div className="flex min-w-0 items-center gap-1.5">
              <select
                aria-label="Select month"
                value={viewState.month}
                onChange={(e) => handleMonthSelect(Number(e.target.value))}
                className="h-9 min-w-0 rounded-md border border-input bg-background px-1 text-base sm:h-7 sm:px-1.5 sm:text-xs font-semibold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {MONTH_NAMES.map((name, idx) => (
                  <option key={name} value={idx}>
                    {name}
                  </option>
                ))}
              </select>

              <select
                aria-label="Select year"
                value={viewState.year}
                onChange={(e) => handleYearSelect(Number(e.target.value))}
                className="h-9 shrink-0 rounded-md border border-input bg-background px-1 text-base sm:h-7 sm:px-1.5 sm:text-xs font-semibold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={handleNextMonth}
              className="h-10 w-10 shrink-0 sm:h-9 sm:w-9 inline-flex items-center justify-center rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
              aria-label="Next month"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Days of Week */}
          <div className="grid grid-cols-7 pt-2 text-center text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            {DAYS_OF_WEEK.map((d) => (
              <div key={d} className="py-1">
                {d}
              </div>
            ))}
          </div>

          {/* Day Grid */}
          <div className="grid grid-cols-7 gap-1 pt-1">
            {calendarDays.map((day, idx) => {
              if (!day.isCurrentMonth) {
                return (
                  <div
                    key={`overflow-${idx}`}
                    className="h-9 w-full sm:h-8 sm:w-8 mx-auto flex items-center justify-center text-xs text-muted-foreground/30 pointer-events-none select-none"
                  >
                    {day.dayNumber}
                  </div>
                );
              }

              return (
                <button
                  type="button"
                  key={day.dateStr}
                  disabled={day.isDisabled}
                  onClick={() => handleSelectDay(day.dateStr)}
                  onMouseEnter={() => setHoveredDate(day.dateStr)}
                  onMouseLeave={() => setHoveredDate(null)}
                  className={cn(
                    "h-9 w-full sm:h-8 sm:w-8 mx-auto flex items-center justify-center rounded-md text-xs sm:text-sm transition-all relative font-medium",
                    // Today outline
                    day.isToday &&
                      !day.isSelected &&
                      "font-bold underline decoration-primary decoration-2 underline-offset-4",
                    // Check-in start date marker
                    day.isStartDate &&
                      "border-2 border-primary text-primary font-bold bg-primary/10",
                    // In-range preview
                    day.isInRange && "bg-primary/15 text-primary rounded-none",
                    // Selected state
                    day.isSelected &&
                      "bg-primary text-primary-foreground font-semibold shadow hover:bg-primary/90",
                    // Hover state for valid unselected days
                    !day.isSelected &&
                      !day.isDisabled &&
                      !day.isStartDate &&
                      "hover:bg-accent hover:text-accent-foreground",
                    // Disabled state
                    day.isDisabled &&
                      "opacity-25 cursor-not-allowed line-through hover:bg-transparent text-muted-foreground",
                  )}
                  title={
                    day.isStartDate
                      ? "Check-in Date"
                      : day.isToday
                        ? "Today"
                        : undefined
                  }
                >
                  {day.dayNumber}
                </button>
              );
            })}
          </div>

          {/* Live stay duration preview if in check-out mode */}
          {startDate && previewStayNights !== null && (
            <div className="mt-2 text-center text-xs font-medium text-primary bg-primary/10 rounded py-1">
              {previewStayNights}{" "}
              {previewStayNights === 1 ? "night stay" : "nights stay"}
            </div>
          )}

          {/* Presets footer */}
          {presets.length > 0 && (
            <div className="mt-2.5 pt-2.5 border-t">
              <div className="text-[10px] uppercase font-semibold text-muted-foreground mb-1.5 px-0.5">
                {startDate ? "Quick Durations" : "Quick Dates"}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                {presets.map((preset) => (
                  <button
                    type="button"
                    key={preset.label}
                    onClick={() => handleSelectDay(preset.date)}
                    className={cn(
                      "rounded border border-input bg-background/50 px-2 py-1 text-xs font-medium hover:bg-accent hover:text-accent-foreground transition-colors text-center truncate",
                      value === preset.date &&
                        "border-primary bg-primary/10 text-primary font-semibold",
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
