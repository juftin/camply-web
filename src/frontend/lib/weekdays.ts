/** Booking weekdays use Monday=0 through Sunday=6, independently of timezones. */
export const WEEKDAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

export const ALL_WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

/** Describe a saved preference, including older scans without a selection. */
export function formatAllowedWeekdays(days?: number[]): string {
  if (!days || new Set(days).size === 7) return "Any night";
  return ALL_WEEKDAYS.filter((day) => days.includes(day))
    .map((day) => WEEKDAY_NAMES[day])
    .join(", ");
}

/** Determine calendar feasibility before starting or changing a saved scan. */
export function hasQualifyingStay(
  start: string,
  end: string,
  days: number[],
  minimum: number,
  today: string = new Date().toISOString().slice(0, 10),
): boolean {
  const night = new Date(`${start > today ? start : today}T00:00:00Z`);
  const checkout = new Date(`${end}T00:00:00Z`);
  let consecutive = 0;
  while (night < checkout) {
    const weekday = (night.getUTCDay() + 6) % 7;
    consecutive = days.includes(weekday) ? consecutive + 1 : 0;
    if (consecutive >= minimum) return true;
    night.setUTCDate(night.getUTCDate() + 1);
  }
  return false;
}
