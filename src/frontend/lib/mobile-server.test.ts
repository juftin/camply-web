import { beforeEach, describe, expect, it, vi } from "vitest";
import { Capacitor } from "@capacitor/core";
import { getMobileServer, saveMobileServer } from "./mobile-server";

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: vi.fn() },
}));

beforeEach(() => {
  vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
  localStorage.clear();
});

describe("mobile server settings", () => {
  it("defaults to camply.rocks", () => {
    expect(getMobileServer()).toEqual({
      url: "https://camply.rocks/",
      auth0ClientId: "",
    });
  });

  it("persists an HTTPS path and the native Auth0 client ID together", () => {
    saveMobileServer(" https://camply.example:8443/trips/ ", " native-client ");
    expect(getMobileServer()).toEqual({
      url: "https://camply.example:8443/trips/",
      auth0ClientId: "native-client",
    });
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    expect(getMobileServer()).toBeNull();
  });

  it.each([
    "",
    "camply.example",
    "http://camply.example",
    "https:camply.example",
    "https://*.camply.example",
    "https://user:password@camply.example",
    "https://camply.example/trips?debug=1",
    "https://camply.example/trips#login",
  ])("rejects an invalid deployment %s", (url) => {
    expect(() => saveMobileServer(url, "")).toThrow(/HTTPS/);
    expect(getMobileServer()?.url).toBe("https://camply.rocks/");
  });
});
