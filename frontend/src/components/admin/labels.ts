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
      // Legacy names for backwards compatibility
      "worker.tasks.heartbeat.discover_targets": "Schedule availability checks",
      "worker.tasks.scanner.check_target_availability":
        "Check campsite availability",
      "worker.tasks.notifications.send_pushover_notification":
        "Send Pushover notification",
      "worker.tasks.ingestion.populate_database": "Sync all provider catalogs",
      "worker.tasks.ingestion.populate_provider_database":
        "Sync provider catalog",
    }[name] ?? name
  );
}
