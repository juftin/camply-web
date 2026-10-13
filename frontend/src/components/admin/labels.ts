/** Display names for known tasks; unknown task identifiers remain visible. */
export function taskLabel(name: string): string {
  return (
    {
      "search.schedule-checks": "Schedule availability checks",
      "search.check-availability": "Check campsite availability",
      "notifications.send-pushover": "Send Pushover notification",
      "catalog.sync-all": "Sync all provider catalogs",
      "catalog.sync-provider": "Sync provider catalog",
    }[name] ?? name
  );
}
