/** Synthetic admin responses for deterministic screenshot capture. */
import type { Page } from "@playwright/test";
import type {
  AdminScanItem,
  AdminUserDetailResponse,
  TrendMetric,
} from "../src/lib/structs";

const NOW = "2026-10-10T12:00:00Z";
const USERS: AdminUserDetailResponse[] = [
  {
    id: "user-snap-1",
    email: "admin@example.test",
    auth0_id: null,
    is_admin: true,
    is_invited: true,
    scanning_enabled: true,
    has_pushover_token: true,
    total_scans: 2,
    active_scans: 1,
    created_at: "2026-10-01T12:00:00Z",
    updated_at: NOW,
  },
  {
    id: "user-snap-2",
    email: "camper@example.test",
    auth0_id: "synthetic|camper",
    is_admin: false,
    is_invited: true,
    scanning_enabled: false,
    has_pushover_token: true,
    total_scans: 1,
    active_scans: 1,
    created_at: "2026-10-05T12:00:00Z",
    updated_at: NOW,
  },
];
const SCANS: AdminScanItem[] = USERS.map((user, index) => ({
  id: `scan-mock-${index + 1}`,
  user_id: user.id,
  user_email: user.email,
  target_id: "target-mock-1",
  provider_id: 1,
  campground_id: "232447",
  campground_name: "Upper Pines Campground",
  start_date: "2026-11-15",
  end_date: "2026-11-19",
  is_active: true,
  is_eligible: user.scanning_enabled,
  user_scanning_enabled: user.scanning_enabled,
  last_checked_at: NOW,
  found_count: 2,
  created_at: user.created_at,
}));
const TASKS = [
  {
    task_id: "task-mock-1",
    event_id: "event-mock-1",
    attempt: 1,
    task_name: "camply.search.check_campsite_availability",
    worker: "celery@worker-1",
    finished_at: NOW,
    duration_ms: 1250,
    entity_type: "target",
    entity_id: "target-mock-1",
    outcome: "success",
    reason: null,
    provider_id: 1,
    provider_name: "Recreation.gov",
    search_name: "Upper Pines",
    search_dates: "2026-11-15 → 2026-11-17",
  },
  {
    task_id: "task-mock-2",
    event_id: "event-mock-2",
    attempt: 1,
    task_name: "camply.notifications.send_pushover_notification",
    worker: "celery@worker-1",
    finished_at: NOW,
    duration_ms: 30,
    entity_type: "scan",
    entity_id: "scan-mock-2",
    outcome: "skipped",
    reason: "scanning_disabled",
    provider_id: 1,
    provider_name: "Recreation.gov",
    search_name: "Upper Pines",
    search_dates: "2026-11-15 → 2026-11-17",
  },
];
const RESULTS = [
  {
    campsite_id: "site-042",
    campsite_name: "Site 042",
    available_dates: ["2026-11-15", "2026-11-16"],
  },
];

/** Provide populated trend series without querying monitoring infrastructure. */
function trendMetrics(group: string): TrendMetric[] {
  const definitions: Record<
    string,
    [string, string, string, "line" | "bar", string[]][]
  > = {
    usage: [
      [
        "users",
        "Registered Users",
        "Total registered users over time.",
        "line",
        ["Total users"],
      ],
      [
        "scans_created",
        "Scans Created",
        "Estimated saved scans created in the preceding 15 minutes.",
        "bar",
        ["New scans"],
      ],
      [
        "scan_activity",
        "Active Settings and Check Eligibility",
        "Active includes suspended owners. Eligible means active with owner scanning access enabled.",
        "line",
        ["Scans Set to Active", "Scans Eligible for Checks"],
      ],
      [
        "search_requests",
        "Campground Search Requests",
        "Campground and recreation area search requests per second.",
        "bar",
        ["Requests"],
      ],
    ],
    worker: [
      [
        "tasks",
        "Task Results",
        "Results per minute: success, error, skipped (no work needed), or retrying (another attempt planned).",
        "line",
        ["Success", "Skipped"],
      ],
      [
        "duration",
        "Task Execution Time",
        "Estimated execution times: 50%, 95%, and 99% of tasks finish within the corresponding value.",
        "line",
        ["Median (p50)", "95th Percentile (p95)", "99th Percentile (p99)"],
      ],
    ],
    api: [
      [
        "http",
        "API Traffic",
        "Requests by status class.",
        "line",
        ["2xx", "4xx", "5xx"],
      ],
    ],
    provider: [
      [
        "provider_errors",
        "Provider Errors",
        "Errors per bucket by booking provider.",
        "bar",
        ["Recreation.gov"],
      ],
    ],
  };
  return (definitions[group] ?? definitions.usage).map(
    ([metric_id, title, description, chart_type, names]) => ({
      metric_id,
      title,
      description,
      chart_type,
      unit:
        {
          users: "users",
          scans_created: "scans",
          scan_activity: "scans",
          search_requests: "req/s",
          tasks: "outcomes/min",
          duration: "ms",
          http: "req/s",
          provider_errors: "errors/s",
        }[metric_id] ?? "count",
      series: names.map((name, seriesIndex) => ({
        name,
        labels: {},
        points: Array.from({ length: 25 }, (_, index) => ({
          timestamp: new Date(
            Date.parse(NOW) - (24 - index) * 3600000,
          ).toISOString(),
          value:
            metric_id === "users"
              ? 3 + Math.floor((index * 9) / 24)
              : metric_id === "scan_activity"
                ? 4 + (index * 2) / 3 + (seriesIndex === 0 ? 0 : -3)
                : Math.max(
                    0,
                    (seriesIndex + 1) * 3 +
                      index +
                      Math.round(Math.sin(index / 3) * 4),
                  ),
        })),
      })),
    }),
  );
}

/** Intercept admin GET endpoints with safe, synthetic data. */
export async function setupAdminSnapshotMocks(
  page: Page,
  options: { partialOperations?: boolean; missingMeasurements?: boolean } = {},
): Promise<void> {
  await page.route("**/api/admin/**", async (route) => {
    const url = new URL(route.request().url());
    const endpoint = url.pathname.replace(/^.*\/api\/admin\//, "");
    let body: unknown;
    if (endpoint === "overview") {
      body = {
        total_users: 12,
        scanning_enabled_users: 10,
        suspended_users: 2,
        total_scans: 24,
        saved_active_scans: 20,
        eligible_scans: 17,
        total_targets: 8,
        eligible_targets: 6,
        dormant_targets: 2,
        overdue_targets: 1,
        heartbeat_interval_seconds: 60,
        target_cooldown_seconds: 55,
        overdue_threshold_seconds: 175,
      };
    } else if (endpoint === "users") {
      body = { users: USERS, total: USERS.length };
    } else if (endpoint.startsWith("users/")) {
      body = USERS.find((user) => endpoint.endsWith(user.id));
    } else if (endpoint === "scans") {
      const owner = url.searchParams.get("owner_id");
      const scans = owner
        ? SCANS.filter((scan) => scan.user_id === owner)
        : SCANS;
      body = { scans, total: scans.length };
    } else if (endpoint.startsWith("scans/")) {
      body = {
        ...SCANS.find((scan) => endpoint.endsWith(scan.id)),
        min_stay_length: 2,
        preferred_types: ["TENT ONLY"],
        require_electric: false,
        recreation_area_name: "Yosemite",
        results: RESULTS,
      };
    } else if (endpoint.startsWith("targets/")) {
      body = {
        id: "target-mock-1",
        provider_id: 1,
        campground_id: "232447",
        campground_name: "Upper Pines Campground",
        start_date: "2026-11-15",
        end_date: "2026-11-19",
        hash: "synthetic-target-hash",
        last_checked_at: NOW,
        created_at: USERS[0].created_at,
        total_subscribers: 2,
        eligible_subscribers: 1,
        status: "active",
        overdue_threshold_seconds: 175,
        subscribers: SCANS.map((scan) => ({
          scan_id: scan.id,
          user_id: scan.user_id,
          user_email: scan.user_email,
          is_active: scan.is_active,
          is_eligible: scan.is_eligible,
          user_scanning_enabled: scan.user_scanning_enabled,
          created_at: scan.created_at,
        })),
        subscribers_total: 2,
      };
    } else if (endpoint === "audit") {
      body = {
        events: [
          {
            id: "audit-mock-1",
            actor_id: USERS[0].id,
            actor_email: USERS[0].email,
            action: "user.scanning_enabled",
            subject_type: "user",
            subject_id: USERS[1].id,
            prev_value: true,
            new_value: false,
            created_at: NOW,
          },
        ],
        total: 1,
      };
    } else if (endpoint === "operations") {
      body = {
        workers: [
          {
            name: "celery@worker-1",
            status: "online",
            active_tasks: options.partialOperations ? null : 2,
            reserved_tasks: 3,
            scheduled_tasks: 1,
          },
        ],
        queue_depth: 7,
        active_tasks_total: options.partialOperations ? null : 2,
        reserved_tasks_total: 3,
        scheduled_tasks_total: 1,
        last_discovery: {
          timestamp: NOW,
          targets_discovered: 6,
          targets_enqueued: 4,
          status: "success",
        },
        broker_connected: true,
        inspection_available: !options.partialOperations,
        telemetry_available: true,
        stale: Boolean(options.partialOperations),
        error_message: options.partialOperations
          ? "Worker inspection incomplete"
          : null,
        last_successful_at: options.partialOperations ? null : NOW,
        snapshot_at: NOW,
      };
    } else if (endpoint === "operations/tasks") {
      body = { tasks: TASKS, total: TASKS.length, available: true };
    } else if (endpoint.startsWith("operations/tasks/")) {
      body = TASKS.find((task) => endpoint.endsWith(task.task_id));
    } else if (endpoint === "trends") {
      const group = url.searchParams.get("group") ?? "usage";
      const metrics = trendMetrics(group);
      if (options.missingMeasurements) {
        for (const metric of metrics) {
          for (const series of metric.series ?? []) {
            if (series.points?.[0]) series.points[0].value = null;
            if (series.points?.[1]) series.points[1].value = 0;
          }
        }
      }
      body = {
        group,
        range: url.searchParams.get("range") ?? "24h",
        step_seconds: 3600,
        start_time: "2026-10-09T12:00:00Z",
        end_time: NOW,
        timezone: "UTC",
        available: true,
        last_successful_at: NOW,
        error_message: null,
        metrics,
      };
    }
    await route.fulfill({
      status: body ? 200 : 404,
      contentType: "application/json",
      body: JSON.stringify(body ?? { detail: "Synthetic endpoint not found" }),
    });
  });
}
