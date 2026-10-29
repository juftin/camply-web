import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AdminOperations } from "./AdminOperations";
import * as api from "@/lib/api";

vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactNode }) => (
      <div style={{ width: 500, height: 300 }}>{children}</div>
    ),
  };
});

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    getAdminOperations: vi.fn(),
    listAdminOperationsTasks: vi.fn(),
    getAdminOperationsTask: vi.fn(),
    getAdminTrends: vi.fn(),
    syncAdminProviders: vi.fn(),
  };
});

let queryClient: QueryClient;

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  vi.clearAllMocks();
  vi.mocked(api.getAdminTrends).mockResolvedValue({
    group: "worker",
    range: "24h",
    step_seconds: 900,
    start_time: "2026-10-09T00:00:00Z",
    end_time: "2026-10-09T01:00:00Z",
    timezone: "UTC",
    available: true,
    error_message: null,
    metrics: [],
  });
});

describe("AdminOperations", () => {
  it("explains local monitoring limits without fetching trends or reporting a broker outage", async () => {
    vi.mocked(api.getAdminOperations).mockResolvedValue({
      runtime_mode: "standalone",
      inspection_available: true,
      telemetry_available: true,
      stale: false,
      capabilities: {
        broker: false,
        historical_trends: false,
        persistent_job_history: false,
      },
      scheduler_status: "running",
      workers: [],
      queue_depth: 0,
      active_tasks_total: 0,
      reserved_tasks_total: null,
      scheduled_tasks_total: null,
      broker_connected: null,
      snapshot_at: "2026-10-14T00:00:00Z",
    });
    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [],
      total: 0,
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(
      await screen.findByText(/historical trends are disabled in standalone/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/history clears on restart/i)).toBeInTheDocument();
    expect(screen.queryByText("Disconnected")).not.toBeInTheDocument();
    expect(api.getAdminTrends).not.toHaveBeenCalled();
  });

  it("renders operations metrics, worker nodes, and telemetry", async () => {
    vi.mocked(api.getAdminOperations).mockResolvedValue({
      runtime_mode: "distributed",
      inspection_available: true,
      telemetry_available: true,
      stale: false,
      workers: [
        {
          name: "celery@worker-node-1",
          status: "online",
          active_tasks: 2,
          reserved_tasks: 5,
          scheduled_tasks: 0,
        },
      ],
      queue_depth: 14,
      active_tasks_total: 2,
      reserved_tasks_total: 5,
      scheduled_tasks_total: 0,
      last_discovery: {
        timestamp: "2026-10-09T01:00:00Z",
        targets_discovered: 12,
        targets_enqueued: 4,
        status: "success",
      },
      broker_connected: true,
      snapshot_at: "2026-10-09T01:05:00Z",
    });

    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [
        {
          task_id: "task-abc-123",
          task_name: "camply.search.check_campsite_availability",
          worker: "celery@worker-node-1",
          finished_at: "2026-10-09T01:04:30Z",
          duration_ms: 1250,
          entity_type: "target",
          entity_id: "target-uuid-9999",
          outcome: "success",
          reason: null,
          provider_id: 1,
          provider_name: "Recreation.gov",
          search_name: "Upper Pines",
          search_dates: "2026-11-01 → 2026-11-03",
        },
      ],
      total: 1,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Header and connection
    await waitFor(() => {
      expect(screen.getByText("System Operations")).toBeInTheDocument();
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // Metric cards
    expect(screen.getByText("14")).toBeInTheDocument(); // queue depth
    expect(screen.getAllByText("2").length).toBeGreaterThan(0); // active tasks & worker table
    expect(screen.getAllByText("5").length).toBeGreaterThan(0); // reserved tasks & worker table

    // Discovery section
    expect(screen.getByText("Latest Scheduling Run")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument(); // targets discovered
    expect(screen.getByText("4")).toBeInTheDocument(); // targets enqueued

    expect(screen.getByText("online")).toHaveClass("bg-emerald-600");

    // Worker node table
    expect(screen.getAllByText("celery@worker-node-1").length).toBeGreaterThan(
      0,
    );

    // Telemetry stream
    expect(screen.getByText("Check campsite availability")).toBeInTheDocument();
    expect(screen.getAllByText("Recreation.gov").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText("Upper Pines")).toBeInTheDocument();
    expect(screen.getByText("2026-11-01 → 2026-11-03")).toBeInTheDocument();
    expect(screen.getByText("target: target-u…")).toBeInTheDocument();
    expect(screen.getByText("1.25 s")).toBeInTheDocument();
  });

  it("opens task detail dialog when details button is clicked", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getAdminOperations).mockResolvedValue({
      runtime_mode: "distributed",
      inspection_available: true,
      telemetry_available: true,
      stale: false,
      workers: [],
      queue_depth: 0,
      active_tasks_total: 0,
      reserved_tasks_total: 0,
      scheduled_tasks_total: 0,
      last_discovery: null,
      broker_connected: true,
      snapshot_at: "2026-10-09T01:05:00Z",
    });

    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [
        {
          task_id: "task-xyz-789",
          task_name: "camply.search.check_campsite_availability",
          worker: "celery@worker-node-2",
          finished_at: "2026-10-09T01:04:30Z",
          duration_ms: 450,
          entity_type: "scan",
          entity_id: "scan-uuid-1111",
          outcome: "error",
          reason: "Rate limited by upstream provider",
          provider_id: 1,
          provider_name: "Recreation.gov",
          search_name: "Lower Pines",
        },
      ],
      total: 1,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Details")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Details"));

    await waitFor(() => {
      expect(screen.getByText("Task Execution Details")).toBeInTheDocument();
      expect(screen.getByText("task-xyz-789")).toBeInTheDocument();
      expect(screen.getAllByText("Lower Pines").length).toBeGreaterThanOrEqual(
        2,
      );
      expect(
        screen.getByText("Rate limited by upstream provider"),
      ).toBeInTheDocument();
    });
  });

  it("handles broker disconnected or error state", async () => {
    vi.mocked(api.getAdminOperations).mockRejectedValue(
      new Error("Broker connection timeout"),
    );
    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [],
      total: 0,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getByText("Operations inspection unavailable"),
      ).toBeInTheDocument();
      expect(screen.getByText("Broker connection timeout")).toBeInTheDocument();
    });
  });

  it("triggers provider sync and displays success feedback when Sync Providers button is clicked", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getAdminOperations).mockResolvedValue({
      runtime_mode: "distributed",
      inspection_available: true,
      telemetry_available: true,
      stale: false,
      workers: [],
      queue_depth: 0,
      active_tasks_total: 0,
      reserved_tasks_total: 0,
      scheduled_tasks_total: 0,
      last_discovery: null,
      broker_connected: true,
      snapshot_at: "2026-10-09T01:05:00Z",
    });

    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [],
      total: 0,
    });

    vi.mocked(api.syncAdminProviders).mockResolvedValue({
      task_id: "task-sync-123",
      status: "queued",
      message: "Metadata sync initiated for all providers.",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const syncButton = await screen.findByRole("button", {
      name: /Sync Providers/i,
    });
    expect(syncButton).toBeInTheDocument();

    await user.click(syncButton);

    await waitFor(() => {
      expect(api.syncAdminProviders).toHaveBeenCalledTimes(1);
      expect(
        screen.getByText("Metadata sync initiated for all providers."),
      ).toBeInTheDocument();
    });
  });

  it("displays error feedback when provider sync fails", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getAdminOperations).mockResolvedValue({
      runtime_mode: "distributed",
      inspection_available: true,
      telemetry_available: true,
      stale: false,
      workers: [],
      queue_depth: 0,
      active_tasks_total: 0,
      reserved_tasks_total: 0,
      scheduled_tasks_total: 0,
      last_discovery: null,
      broker_connected: true,
      snapshot_at: "2026-10-09T01:05:00Z",
    });

    vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
      available: true,
      tasks: [],
      total: 0,
    });

    vi.mocked(api.syncAdminProviders).mockRejectedValue(
      new Error("Broker unreachable"),
    );

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOperations />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const syncButton = await screen.findByRole("button", {
      name: /Sync Providers/i,
    });
    await user.click(syncButton);

    await waitFor(() => {
      expect(screen.getByText("Broker unreachable")).toBeInTheDocument();
    });
  });
});

it("shows telemetry outages as unavailable instead of idle", async () => {
  vi.mocked(api.getAdminOperations).mockResolvedValue({
    runtime_mode: "distributed",
    workers: [],
    queue_depth: 0,
    active_tasks_total: 0,
    reserved_tasks_total: 0,
    scheduled_tasks_total: 0,
    broker_connected: false,
    inspection_available: false,
    telemetry_available: false,
    stale: true,
    snapshot_at: "2026-10-10T12:00:00Z",
    error_message: "Queue telemetry unavailable",
    last_successful_at: null,
  });
  vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
    tasks: [],
    total: 0,
    available: false,
    error_message: "Task stream unavailable",
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminOperations />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    await screen.findByText(/Queue telemetry unavailable/),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  expect(
    await screen.findByText("Task stream unavailable"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("No recent task results match these filters."),
  ).not.toBeInTheDocument();
});

it("preserves known counts and shows unanswered workload as unknown", async () => {
  vi.mocked(api.getAdminOperations).mockResolvedValue({
    runtime_mode: "distributed",
    workers: [
      {
        name: "worker-1",
        status: "online",
        active_tasks: null,
        reserved_tasks: 0,
        scheduled_tasks: 0,
      },
    ],
    queue_depth: 0,
    active_tasks_total: null,
    reserved_tasks_total: 0,
    scheduled_tasks_total: 0,
    broker_connected: true,
    inspection_available: false,
    telemetry_available: true,
    stale: true,
    snapshot_at: "2026-10-10T12:00:00Z",
    error_message: "Worker inspection incomplete",
  });
  vi.mocked(api.listAdminOperationsTasks).mockResolvedValue({
    tasks: [],
    total: 0,
    available: true,
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminOperations />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(await screen.findByText("worker-1")).toBeInTheDocument();
  expect(screen.getAllByText("Unknown")).toHaveLength(2);
  expect(screen.getByText("Connected")).toBeInTheDocument();
  expect(screen.getAllByText("0").length).toBeGreaterThan(0);
});
