/** Display names for known tasks; unknown task identifiers remain visible. */
export function taskLabel(name: string): string {
  return (
    {
      "worker.tasks.heartbeat.discover_targets": "Schedule availability checks",
      "worker.tasks.scanner.check_target_availability":
        "Check campsite availability",
      "worker.tasks.notifications.send_pushover_notification":
        "Send Pushover notification",
    }[name] ?? name
  );
}
