/** Display names for known tasks; unknown task identifiers remain visible. */
export function taskLabel(name: string): string {
  return (
    {
      "camply.search.schedule_checks": "Schedule availability checks",
      "camply.search.check_campsite_availability":
        "Check campsite availability",
      "camply.notifications.send_pushover_notification":
        "Send Pushover notification",
      "camply.catalog.sync_all_providers": "Sync all provider catalogs",
      "camply.catalog.sync_provider_catalog": "Sync provider catalog",
    }[name] ?? name
  );
}
