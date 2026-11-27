import { describe, expect, it } from "vitest";
import { mobileApiUrl } from "./mobile-build";

describe("mobile API URL", () => {
  it.each([
    ["https://camply.example", "https://camply.example/api"],
    [
      "https://camply.example:8443/camply/",
      "https://camply.example:8443/camply/api",
    ],
  ])("resolves %s to its API", (deployment, api) => {
    expect(mobileApiUrl(deployment)).toBe(api);
  });

  it.each([
    undefined,
    "camply.example",
    "http://camply.example",
    "https:camply.example",
    "https://*.camply.example",
    "https://user:password@camply.example",
    "https://camply.example/camply?debug=1",
    "https://camply.example/camply#login",
  ])("rejects an invalid deployment %s", (deployment) => {
    expect(() => mobileApiUrl(deployment)).toThrow(/CAMPLY_MOBILE_URL/);
  });
});
