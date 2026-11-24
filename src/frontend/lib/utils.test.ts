import { describe, expect, it, vi, afterEach } from "vitest";
import {
  toTitleCase,
  formatRelativeTime,
  parseDateTime,
  parseIsoDate,
  toIsoDateString,
  getTodayString,
  addDays,
  daysBetween,
  formatDisplayDate,
  getUpcomingFriday,
} from "./utils";

describe("toTitleCase", () => {
  it("title-cases an all-uppercase string", () => {
    expect(toTitleCase("YOSEMITE NATIONAL PARK")).toBe(
      "Yosemite National Park",
    );
  });

  it("title-cases an all-lowercase string", () => {
    expect(toTitleCase("yosemite national park")).toBe(
      "Yosemite National Park",
    );
  });

  it("leaves a properly-cased mixed-case string unchanged", () => {
    expect(toTitleCase("Yosemite National Park")).toBe(
      "Yosemite National Park",
    );
  });

  it("leaves a mixed-case string with capital-in-middle unchanged", () => {
    expect(toTitleCase("McKinney Lake")).toBe("McKinney Lake");
  });

  it("returns an empty string unchanged", () => {
    expect(toTitleCase("")).toBe("");
  });

  it("capitalizes the first word even when it is an exception word", () => {
    expect(toTitleCase("OF MICE AND MEN")).toBe("Of Mice and Men");
  });

  it("lowercases inner exception words", () => {
    expect(toTitleCase("THE LORD OF THE RINGS")).toBe("The Lord of the Rings");
  });

  it("handles multiple consecutive spaces in all-upper input", () => {
    expect(toTitleCase("YOSEMITE  NATIONAL  PARK")).toBe(
      "Yosemite  National  Park",
    );
  });

  it("handles a single word uppercase", () => {
    expect(toTitleCase("CAMPING")).toBe("Camping");
  });

  it("handles a single word lowercase", () => {
    expect(toTitleCase("camping")).toBe("Camping");
  });

  it("handles a single word mixed case", () => {
    expect(toTitleCase("Camping")).toBe("Camping");
  });

  it("handles a string with leading whitespace mixed case", () => {
    expect(toTitleCase("  Yosemite")).toBe("  Yosemite");
  });

  it("handles a string with trailing whitespace all-caps", () => {
    expect(toTitleCase("YOSEMITE ")).toBe("Yosemite ");
  });
});

describe("formatRelativeTime", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not throw for a valid ISO string", () => {
    expect(() => formatRelativeTime("2020-01-01T00:00:00Z")).not.toThrow();
  });

  it("shows seconds ago for timestamps within the last minute", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T11:59:30Z")).toBe("30s ago");
    expect(formatRelativeTime("2025-06-15T11:59:01Z")).toBe("59s ago");
  });

  it("shows minutes ago for timestamps in the last hour", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T11:59:00Z")).toBe("1m ago");
    expect(formatRelativeTime("2025-06-15T11:30:00Z")).toBe("30m ago");
  });

  it("shows hours ago for timestamps in the last day", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T10:00:00Z")).toBe("2h ago");
  });

  it("shows days ago for older timestamps", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-12T12:00:00Z")).toBe("3d ago");
  });

  it("returns 'just now' for timestamps slightly in the future (clock skew)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T12:00:30Z")).toBe("just now");
    expect(formatRelativeTime("2025-06-15T12:00:59Z")).toBe("just now");
  });

  it("uses future tense for timestamps further in the future", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T12:05:00Z")).toBe("in 5m");
    expect(formatRelativeTime("2025-06-15T14:00:00Z")).toBe("in 2h");
    expect(formatRelativeTime("2025-06-18T12:00:00Z")).toBe("in 3d");
  });

  it("parses naive ISO timestamps (without Z) as UTC instead of local time", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-06-15T12:00:00Z"));

    expect(formatRelativeTime("2025-06-15T11:59:30")).toBe("30s ago");
    expect(formatRelativeTime("2025-06-15T11:30:00")).toBe("30m ago");
    expect(formatRelativeTime("2025-06-15T10:00:00")).toBe("2h ago");
  });

  it("returns empty string for empty input or invalid date", () => {
    expect(formatRelativeTime("")).toBe("");
    expect(formatRelativeTime("not-a-date")).toBe("");
  });
});

describe("parseDateTime", () => {
  it("parses naive ISO date-time as UTC", () => {
    const d = parseDateTime("2026-10-14T03:54:33");
    expect(d.toISOString()).toBe("2026-10-14T03:54:33.000Z");
  });

  it("parses aware ISO date-time with Z as UTC", () => {
    const d = parseDateTime("2026-10-14T03:54:33Z");
    expect(d.toISOString()).toBe("2026-10-14T03:54:33.000Z");
  });

  it("parses ISO date-time with timezone offset", () => {
    const d = parseDateTime("2026-10-14T03:54:33-05:00");
    expect(d.toISOString()).toBe("2026-10-14T08:54:33.000Z");
  });

  it("parses date-only string as UTC midnight", () => {
    const d = parseDateTime("2026-10-14");
    expect(d.toISOString()).toBe("2026-10-14T00:00:00.000Z");
  });
});

describe("date helpers", () => {
  it("parseIsoDate and toIsoDateString roundtrip correctly", () => {
    const iso = "2026-10-15";
    const d = parseIsoDate(iso);
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(9); // 0-indexed month (October)
    expect(d.getDate()).toBe(15);
    expect(toIsoDateString(d)).toBe(iso);
  });

  it("getTodayString returns a valid YYYY-MM-DD string", () => {
    expect(getTodayString()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("addDays correctly increments and decrements dates across month and year boundaries", () => {
    expect(addDays("2026-10-15", 3)).toBe("2026-10-18");
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-01-01", -1)).toBe("2025-12-31");
    expect(addDays("2028-02-28", 1)).toBe("2028-02-29"); // Leap year
    expect(addDays("2028-02-29", 1)).toBe("2028-03-01");
  });

  it("daysBetween computes absolute night count between dates", () => {
    expect(daysBetween("2026-10-15", "2026-10-18")).toBe(3);
    expect(daysBetween("2026-10-15", "2026-10-15")).toBe(0);
    expect(daysBetween("2026-10-18", "2026-10-15")).toBe(0);
  });

  it("formatDisplayDate formats date for humans with and without weekday", () => {
    const formattedWithDay = formatDisplayDate("2026-10-15", true);
    expect(formattedWithDay).toContain("Oct 15, 2026");
    expect(formattedWithDay).toContain("Thu");

    const formattedWithoutDay = formatDisplayDate("2026-10-15", false);
    expect(formattedWithoutDay).toBe("Oct 15, 2026");

    expect(formatDisplayDate("")).toBe("");
  });

  it("getUpcomingFriday calculates the correct next Friday", () => {
    // 2026-10-13 is Tuesday (day 2) -> upcoming Friday is 2026-10-16
    expect(getUpcomingFriday("2026-10-13")).toBe("2026-10-16");
    // 2026-10-16 is Friday -> next upcoming Friday is 2026-10-23
    expect(getUpcomingFriday("2026-10-16")).toBe("2026-10-23");
  });
});
