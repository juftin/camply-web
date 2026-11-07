import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  enableNativeNotifications,
  notifyOpening,
  OpeningTracker,
} from "./mobile-notifications";
import type { ScanDetailResponse } from "./structs";

const mocks = vi.hoisted(() => ({
  invoke: vi.fn(),
  native: vi.fn(),
  granted: vi.fn(),
  request: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({
  isTauri: mocks.native,
  invoke: mocks.invoke,
}));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: mocks.granted,
  requestPermission: mocks.request,
}));
const scan = (
  dates: string[],
  id = "scan-1",
  active = true,
): ScanDetailResponse => ({
  id,
  is_active: active,
  provider_id: 1,
  campground_id: "camp",
  campground_name: "Park",
  recreation_area_name: "Park",
  start_date: "2027-01-01",
  end_date: "2027-01-04",
  min_stay_length: 1,
  require_electric: false,
  preferred_types: [],
  last_checked_at: null,
  found_count: dates.length,
  created_at: "2026-11-07",
  results: [
    {
      campsite_id: "site",
      campsite_name: "Site",
      booking_url: "https://example.com",
      available_dates: dates,
    },
  ],
});

describe("native permission", () => {
  beforeEach(() => vi.resetAllMocks());
  it("does not request permissions in a browser", async () => {
    mocks.native.mockReturnValue(false);
    expect(await enableNativeNotifications()).toBe(false);
    expect(mocks.request).not.toHaveBeenCalled();
  });
  it("accepts an existing grant without prompting", async () => {
    mocks.native.mockReturnValue(true);
    mocks.granted.mockResolvedValue(true);
    expect(await enableNativeNotifications()).toBe(true);
    expect(mocks.request).not.toHaveBeenCalled();
  });
  it.each(["granted", "denied"])("handles %s", async (permission) => {
    mocks.native.mockReturnValue(true);
    mocks.granted.mockResolvedValue(false);
    mocks.request.mockResolvedValue(permission);
    expect(await enableNativeNotifications()).toBe(permission === "granted");
  });
});

describe("opening detection", () => {
  it("suppresses initial and unchanged results, but detects equal-count replacements", () => {
    const tracker = new OpeningTracker();
    expect(tracker.update([scan(["2027-01-01"])])).toEqual([]);
    expect(tracker.update([scan(["2027-01-01"])])).toEqual([]);
    expect(tracker.update([scan(["2027-01-02"])])).toHaveLength(1);
    expect(tracker.update([scan(["2027-01-02"])])).toEqual([]);
  });
  it("ignores removals, handles reopened dates and baselines new scans", () => {
    const tracker = new OpeningTracker();
    tracker.update([scan(["2027-01-01"])]);
    expect(tracker.update([scan([])])).toEqual([]);
    expect(tracker.update([scan(["2027-01-01"])])).toHaveLength(1);
    expect(tracker.update([scan(["2027-01-01"], "other-user-scan")])).toEqual(
      [],
    );
  });
  it("ignores paused scans and forgets deleted scans", () => {
    const tracker = new OpeningTracker();
    tracker.update([scan([])]);
    expect(tracker.update([scan(["2027-01-01"], "scan-1", false)])).toEqual([]);
    tracker.update([]);
    expect(tracker.update([scan(["2027-01-02"])])).toEqual([]);
  });
});

describe("native delivery", () => {
  beforeEach(() => vi.resetAllMocks());
  it("awaits the native command and reports delivery errors", async () => {
    mocks.granted.mockResolvedValue(true);
    mocks.invoke.mockRejectedValue(new Error("native delivery failed"));
    await expect(notifyOpening(scan([]))).rejects.toThrow(
      "native delivery failed",
    );
    expect(mocks.invoke).toHaveBeenCalledWith("plugin:notification|notify", {
      options: {
        title: "Campsites available",
        body: "New openings at Park. Open Camply to view your scan.",
      },
    });
  });
  it("does not send after OS permission is revoked", async () => {
    mocks.granted.mockResolvedValue(false);
    await expect(notifyOpening(scan([]))).rejects.toThrow("system settings");
    expect(mocks.invoke).not.toHaveBeenCalled();
  });
});
