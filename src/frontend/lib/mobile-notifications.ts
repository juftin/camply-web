import { invoke, isTauri } from "@tauri-apps/api/core";
import type { ScanDetailResponse } from "./structs";

export const nativeNotificationsAvailable = () => isTauri();

export async function enableNativeNotifications(): Promise<boolean> {
  if (!nativeNotificationsAvailable()) return false;
  const { isPermissionGranted, requestPermission } =
    await import("@tauri-apps/plugin-notification");
  return (
    (await isPermissionGranted()) || (await requestPermission()) === "granted"
  );
}

export async function notifyOpening(scan: ScanDetailResponse): Promise<void> {
  const { isPermissionGranted } =
    await import("@tauri-apps/plugin-notification");
  if (!(await isPermissionGranted()))
    throw new Error("Notifications are disabled in system settings.");
  // Await the native command: the plugin's convenience wrapper returns void.
  await invoke("plugin:notification|notify", {
    options: {
      title: "Campsites available",
      body: `New openings at ${scan.campground_name || "your campground"}. Open Camply to view your scan.`,
    },
  });
}

/** Compare individual campsite/date pairs, including replacements at equal counts. */
export class OpeningTracker {
  private previous = new Map<string, Set<string>>();

  update(scans: ScanDetailResponse[]): ScanDetailResponse[] {
    const openings: ScanDetailResponse[] = [];
    const next = new Map<string, Set<string>>();
    for (const scan of scans) {
      const keys = new Set(
        (scan.results ?? []).flatMap((result) =>
          (result.available_dates ?? []).map(
            (date) => `${result.campsite_id}:${date}`,
          ),
        ),
      );
      const previous = this.previous.get(scan.id);
      if (
        scan.is_active &&
        previous &&
        [...keys].some((key) => !previous.has(key))
      ) {
        openings.push(scan);
      }
      next.set(scan.id, keys);
    }
    this.previous = next;
    return openings;
  }
}
