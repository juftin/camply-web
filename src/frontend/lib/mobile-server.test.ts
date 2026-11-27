import { beforeEach, describe, expect, it, vi } from "vitest";
import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";
import {
  getMobileServer,
  loadMobileServer,
  saveMobileServer,
} from "./mobile-server";

vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: vi.fn() },
}));
vi.mock("@capacitor/preferences", () => ({
  Preferences: { get: vi.fn(), set: vi.fn() },
}));

beforeEach(() => {
  vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
  let value: string | null = null;
  vi.mocked(Preferences.get).mockImplementation(async () => ({ value }));
  vi.mocked(Preferences.set).mockImplementation(async ({ value: saved }) => {
    value = saved;
  });
  localStorage.clear();
});

describe("mobile server settings", () => {
  it("defaults to camply.rocks", async () => {
    expect(await loadMobileServer()).toEqual({
      url: "https://camply.rocks/",
      auth0ClientId: "",
    });
  });

  it("keeps the native server selection after WebView storage is cleared", async () => {
    await saveMobileServer(
      " https://camply.example:8443/trips/ ",
      " native-client ",
    );
    localStorage.clear();
    expect(await loadMobileServer()).toEqual({
      url: "https://camply.example:8443/trips/",
      auth0ClientId: "native-client",
    });
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    expect(await loadMobileServer()).toBeNull();
  });

  it("moves a valid legacy WebView setting into native preferences", async () => {
    const settings = {
      url: "https://private.example/trips/",
      auth0ClientId: "private-client",
    };
    localStorage.setItem("camply-mobile-server", JSON.stringify(settings));
    expect(await loadMobileServer()).toEqual(settings);
    expect(Preferences.set).toHaveBeenCalledWith({
      key: "camply-mobile-server",
      value: JSON.stringify(settings),
    });
    expect(localStorage.getItem("camply-mobile-server")).toBeNull();
    expect(getMobileServer()).toEqual(settings);
  });

  it("reports native storage failures instead of selecting the hosted default", async () => {
    vi.mocked(Preferences.get).mockRejectedValueOnce(new Error("Unavailable"));
    await expect(loadMobileServer()).rejects.toThrow("Unavailable");
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
  ])("rejects an invalid deployment %s", async (url) => {
    await expect(saveMobileServer(url, "")).rejects.toThrow(/HTTPS/);
    expect((await loadMobileServer())?.url).toBe("https://camply.rocks/");
  });
});
