import { describe, expect, it } from "vitest";
import {
  ALL_WEEKDAYS,
  formatAllowedWeekdays,
  hasQualifyingStay,
} from "./weekdays";

describe("booking night preferences", () => {
  it("names custom nights in calendar order and describes unrestricted legacy scans", () => {
    expect(formatAllowedWeekdays()).toBe("Any night");
    expect(formatAllowedWeekdays(ALL_WEEKDAYS)).toBe("Any night");
    expect(formatAllowedWeekdays([5, 4, 5])).toBe("Friday, Saturday");
    expect(formatAllowedWeekdays([2, 0])).toBe("Monday, Wednesday");
  });

  it.each([
    ["2027-07-01", "2027-07-05", [4, 5], 2, true],
    ["2027-07-01", "2027-07-05", [4, 5], 3, false],
    ["2027-07-04", "2027-07-06", [0, 6], 2, true],
    ["2027-07-02", "2027-07-03", [4, 5], 2, false],
    ["2027-12-31", "2028-01-02", [4, 5], 2, true],
    ["2028-02-28", "2028-03-02", [0, 2], 2, false],
    ["2027-07-01", "2027-07-05", [], 1, false],
  ])(
    "evaluates occupied nights %s–%s without bridging exclusions",
    (start, end, days, minimum, expected) => {
      expect(hasQualifyingStay(start, end, days, minimum, "2027-01-01")).toBe(
        expected,
      );
    },
  );

  it("expires earlier nights before evaluating the requested stay", () => {
    expect(
      hasQualifyingStay("2027-07-02", "2027-07-04", [4, 5], 2, "2027-07-03"),
    ).toBe(false);
  });
});
