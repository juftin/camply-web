import { describe, expect, it, vi, afterEach } from "vitest";
import { toTitleCase, formatRelativeTime } from "./utils";

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
    expect(toTitleCase("THE LORD OF THE RINGS")).toBe(
      "The Lord of the Rings",
    );
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
});
