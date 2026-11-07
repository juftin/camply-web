import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { getScan, listScans } from "@/lib/api";
import {
  enableNativeNotifications,
  nativeNotificationsAvailable,
  notifyOpening,
  OpeningTracker,
} from "@/lib/mobile-notifications";
import type { ScanDetailResponse } from "@/lib/structs";
import { Button } from "@/components/ui/button";

async function activeScanDetails(): Promise<ScanDetailResponse[]> {
  const details: ScanDetailResponse[] = [];
  for (let offset = 0; ; offset += 200) {
    const page = await listScans({ is_active: true, limit: 200, offset });
    // Bound concurrent API requests for accounts with many saved scans.
    for (let i = 0; i < page.scans.length; i += 5) {
      details.push(
        ...(await Promise.all(
          page.scans.slice(i, i + 5).map((scan) => getScan(scan.id)),
        )),
      );
    }
    if (!page.scans.length || offset + page.scans.length >= page.total) break;
  }
  return details;
}

const AccountNotifications = ({ accountId }: { accountId: string }) => {
  const key = `camply-mobile-notifications:${accountId}`;
  const [enabled, setEnabled] = useState(
    () => localStorage.getItem(key) === "true",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tracker = useRef(new OpeningTracker());
  const query = useQuery({
    queryKey: ["mobile-notifications", accountId],
    queryFn: activeScanDetails,
    enabled,
    retry: false,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    gcTime: 0,
  });

  useEffect(() => {
    if (!enabled || !query.data) return;
    const openings = tracker.current.update(query.data);
    for (const scan of openings) {
      void notifyOpening(scan).catch(() =>
        setError(
          "Could not deliver a notification. Check notification access in system settings.",
        ),
      );
    }
  }, [enabled, query.data]);

  const toggle = async () => {
    setError(null);
    if (enabled) {
      localStorage.removeItem(key);
      setEnabled(false);
      tracker.current = new OpeningTracker();
      return;
    }
    setBusy(true);
    try {
      if (await enableNativeNotifications()) {
        localStorage.setItem(key, "true");
        setEnabled(true);
      } else {
        setError(
          "Notifications are denied. Allow Camply notifications in system settings, then try again.",
        );
      }
    } catch {
      setError("Could not request notification access. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside
      className="border-b px-4 py-3 text-sm"
      aria-label="Mobile notifications"
    >
      <Button
        size="sm"
        variant="outline"
        disabled={busy}
        onClick={() => void toggle()}
      >
        {enabled
          ? "Disable mobile notifications"
          : "Enable mobile notifications"}
      </Button>
      <p className="mt-2 text-muted-foreground">
        Alerts for new openings while Camply is open. Keep server alerts enabled
        for background delivery.
      </p>
      {(error || query.isError) && (
        <p role="alert" className="mt-2 text-destructive">
          {error ||
            "Could not refresh scans for notifications. Retrying in one minute."}
        </p>
      )}
    </aside>
  );
};

const AuthenticatedMobileNotifications = () => {
  const { user, isReady, inviteOnly, isInvited } = useAuth();
  if (
    !isReady ||
    !user ||
    user.must_change_password ||
    (inviteOnly && !isInvited)
  )
    return null;
  return <AccountNotifications key={user.id} accountId={user.id} />;
};

export const MobileNotifications = () =>
  nativeNotificationsAvailable() ? <AuthenticatedMobileNotifications /> : null;
