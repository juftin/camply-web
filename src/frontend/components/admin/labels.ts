interface TaskMetadata {
  label: string;
  description: string;
}

const TASK_METADATA: Record<string, TaskMetadata> = {
  "search.schedule_checks": {
    label: "Schedule availability checks",
    description:
      "Finds active targets due for a check and queues availability scans.",
  },
  "search.check_availability": {
    label: "Check availability",
    description:
      "Queries the booking provider for open campsites and queues alerts for new matches.",
  },
  "notifications.send_pushover": {
    label: "Send Pushover alert",
    description:
      "Delivers a campsite availability alert to a user via Pushover.",
  },
  "notifications.send_ntfy": {
    label: "Send ntfy alert",
    description: "Delivers a campsite availability alert to a user via ntfy.",
  },
  "notifications.send_area_alerts": {
    label: "Send recreation area alerts",
    description:
      "Sends queued availability alerts for multi-campground recreation area scans.",
  },
  "catalog.sync_all": {
    label: "Sync all provider catalogs",
    description:
      "Schedules full catalog imports across all registered booking providers.",
  },
  "catalog.sync_provider": {
    label: "Sync provider catalog",
    description:
      "Imports recreation areas and campgrounds for a single booking provider.",
  },
  "catalog.enrich_all": {
    label: "Enrich all providers",
    description:
      "Schedules destination detail enrichment batches across all registered providers.",
  },
  "catalog.enrich_provider": {
    label: "Enrich provider details",
    description:
      "Fetches descriptions, photos, and metadata for a batch of provider destinations.",
  },
};

const LEGACY_TASK_ALIASES: Record<string, string> = {
  "camply.search.schedule_checks": "search.schedule_checks",
  "camply.search.check_campsite_availability": "search.check_availability",
  "camply.notifications.send_pushover_notification":
    "notifications.send_pushover",
  "camply.notifications.send_ntfy_notification": "notifications.send_ntfy",
  "camply.notifications.deliver_area_outbox": "notifications.send_area_alerts",
  "camply.catalog.sync_all_providers": "catalog.sync_all",
  "camply.catalog.sync_provider_catalog": "catalog.sync_provider",
  "camply.catalog.enrich_all_providers": "catalog.enrich_all",
  "camply.catalog.enrich_provider_details": "catalog.enrich_provider",
};

function resolveTaskMetadata(name: string): TaskMetadata | undefined {
  return TASK_METADATA[LEGACY_TASK_ALIASES[name] ?? name];
}

/** Display names for known tasks; unknown task identifiers remain visible. */
export function taskLabel(name: string): string {
  return resolveTaskMetadata(name)?.label ?? name;
}

/** Brief human-readable description for known tasks. */
export function taskDescription(name: string): string | null {
  return resolveTaskMetadata(name)?.description ?? null;
}
