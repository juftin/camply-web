import { describe, expect, it } from "vitest";
import { authReturnTo } from "./authRedirect";

describe("notification login destinations", () => {
  it("preserves a scan's results destination", () => {
    expect(authReturnTo("/dashboard/scans/scan-1#results")).toBe(
      "/dashboard/scans/scan-1#results",
    );
  });
  it.each([
    null,
    "https://other.example",
    "//other.example",
    "/\\other.example",
    "//",
    "javascript:alert(1)",
  ])("rejects external destination %s", (destination) => {
    expect(authReturnTo(destination)).toBe("/dashboard");
  });
});
