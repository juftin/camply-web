import { describe, expect, it } from "vitest";
import { toTitleCase } from "./utils";

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
