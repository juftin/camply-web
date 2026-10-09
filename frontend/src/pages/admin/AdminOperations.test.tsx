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
  it("renders operations metrics, worker nodes, and telemetry", async () => {
    vi.mocked(api.getAdminOperations).mockResolvedValue({
      workers: [
        {
          name: "celery@worker-node-1",
          status: "active",
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
      tasks: [
        {
          task_id: "task-abc-123",
          task_name: "worker.tasks.scanner.scan_target",
          worker: "celery@worker-node-1",
          finished_at: "2026-10-09T01:04:30Z",
          duration_ms: 1250,
          entity_type: "target",
          entity_id: "target-uuid-9999",
          outcome: "success",
          reason: null,
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
    expect(screen.getByText("Heartbeat Discovery")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument(); // targets discovered
    expect(screen.getByText("4")).toBeInTheDocument(); // targets enqueued

    // Worker node table
    expect(screen.getAllByText("celery@worker-node-1").length).toBeGreaterThan(
      0,
    );

    // Telemetry stream
    expect(
      screen.getByText("worker.tasks.scanner.scan_target"),
    ).toBeInTheDocument();
    expect(screen.getByText("target: target-u…")).toBeInTheDocument();
    expect(screen.getByText("1.25 s")).toBeInTheDocument();
  });

  it("opens task detail dialog when details button is clicked", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getAdminOperations).mockResolvedValue({
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
      tasks: [
        {
          task_id: "task-xyz-789",
          task_name: "worker.tasks.scanner.scan_target",
          worker: "celery@worker-node-2",
          finished_at: "2026-10-09T01:04:30Z",
          duration_ms: 450,
          entity_type: "scan",
          entity_id: "scan-uuid-1111",
          outcome: "error",
          reason: "Rate limited by upstream provider",
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
});
