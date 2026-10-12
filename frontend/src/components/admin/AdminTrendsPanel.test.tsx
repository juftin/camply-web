import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AdminTrendsPanel } from "./AdminTrendsPanel";
import * as api from "@/lib/api";

it("keeps sources distinguishable and shows units, full times, zeroes, and missing measurements", async () => {
  vi.mocked(api.getAdminTrends).mockResolvedValue({
    group: "api",
    range: "24h",
    step_seconds: 900,
    start_time: "2026-10-09T00:00:00Z",
    end_time: "2026-10-09T01:00:00Z",
    timezone: "UTC",
    available: true,
    metrics: [
      {
        metric_id: "requests",
        title: "API Requests",
        description: "Requests per second.",
        unit: "req/s",
        chart_type: "bar",
        series: [
          {
            name: "Requests (job=backend, instance=api-1:8000)",
            labels: { job: "backend", instance: "api-1:8000" },
            points: [{ timestamp: "2026-10-09T00:00:00Z", value: 0 }],
          },
          {
            name: "Requests (job=backend, instance=api-2:8000)",
            labels: { job: "backend", instance: "api-2:8000" },
            points: [{ timestamp: "2026-10-09T00:15:00Z", value: 1.2345 }],
          },
        ],
      },
    ],
  });
  render(
    <MemoryRouter initialEntries={["/admin/operations?api_view=table"]}>
      <QueryClientProvider client={queryClient}>
        <AdminTrendsPanel group="api" />
      </QueryClientProvider>
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole("columnheader", {
      name: "Requests · api-1:8000 (requests / second)",
    }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("columnheader", {
      name: "Requests · api-2:8000 (requests / second)",
    }),
  ).toBeInTheDocument();
  expect(screen.getByText("0")).toBeInTheDocument();
  expect(
    screen.getByText(
      (1.2345).toLocaleString(undefined, { maximumFractionDigits: 4 }),
    ),
  ).toBeInTheDocument();
  expect(screen.getAllByText("No measurement")).toHaveLength(2);
  expect(
    screen.getByText(new Date("2026-10-09T00:00:00Z").toLocaleString()),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Table" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

// Recharts ResponsiveContainer requires width/height mocking in jsdom
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
    getAdminTrends: vi.fn(),
  };
});

let queryClient: QueryClient;

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  vi.clearAllMocks();
});

describe("AdminTrendsPanel", () => {
  it("renders trend metrics, range controls, and chart toggle", async () => {
    vi.mocked(api.getAdminTrends).mockResolvedValue({
      group: "usage",
      range: "24h",
      step_seconds: 900,
      start_time: "2026-10-09T00:00:00Z",
      end_time: "2026-10-09T01:00:00Z",
      timezone: "UTC",
      available: true,
      error_message: null,
      metrics: [
        {
          metric_id: "registered_users",
          title: "Total Registered Users",
          description: "Cumulative registered users in the database.",
          unit: "users",
          chart_type: "line",
          series: [
            {
              name: "Registered Users",
              labels: {},
              points: [
                { timestamp: "2026-10-09T00:00:00Z", value: 12 },
                { timestamp: "2026-10-09T00:15:00Z", value: 15 },
              ],
            },
          ],
        },
      ],
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminTrendsPanel group="usage" title="Usage Trends" />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Usage Trends")).toBeInTheDocument();
      expect(screen.getByText("Total Registered Users")).toBeInTheDocument();
      expect(screen.getByText("users")).toBeInTheDocument();
    });

    // Check range buttons
    expect(screen.getByText("Last 24 hours")).toBeInTheDocument();
    expect(screen.getByText("Last 7 days")).toBeInTheDocument();
    expect(screen.getByText("Last 30 days")).toBeInTheDocument();
  });

  it("switches to accessible table view on toggle", async () => {
    const user = userEvent.setup();

    vi.mocked(api.getAdminTrends).mockResolvedValue({
      group: "usage",
      range: "24h",
      step_seconds: 900,
      start_time: "2026-10-09T00:00:00Z",
      end_time: "2026-10-09T01:00:00Z",
      timezone: "UTC",
      available: true,
      error_message: null,
      metrics: [
        {
          metric_id: "new_users",
          title: "New Users Created",
          description: "Registrations per bucket.",
          unit: "users",
          chart_type: "bar",
          series: [
            {
              name: "New Users",
              labels: {},
              points: [{ timestamp: "2026-10-09T00:00:00Z", value: 4 }],
            },
          ],
        },
      ],
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminTrendsPanel group="usage" />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("New Users Created")).toBeInTheDocument();
    });

    // Click table toggle button
    const tableButton = screen.getByTitle("Accessible table view");
    await user.click(tableButton);

    await waitFor(() => {
      expect(
        screen.getByRole("columnheader", { name: /^Time \(/ }),
      ).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
    });
  });

  it("renders outage warning banner when Prometheus is unavailable", async () => {
    vi.mocked(api.getAdminTrends).mockResolvedValue({
      group: "worker",
      range: "24h",
      step_seconds: 900,
      start_time: "2026-10-09T00:00:00Z",
      end_time: "2026-10-09T01:00:00Z",
      timezone: "UTC",
      available: false,
      error_message: "Connection refused to Prometheus",
      metrics: [],
    });

    render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <AdminTrendsPanel group="worker" />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Prometheus monitoring unavailable/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Connection refused to Prometheus/i),
      ).toBeInTheDocument();
    });
  });
});

it("restores a chart range from the URL and queries the selected range", async () => {
  vi.mocked(api.getAdminTrends).mockResolvedValue({
    group: "usage",
    range: "7d",
    step_seconds: 3600,
    start_time: "2026-10-03T12:00:00Z",
    end_time: "2026-10-10T12:00:00Z",
    timezone: "UTC",
    available: true,
    metrics: [],
  });
  const browser = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/admin?usage_range=7d&usage_view=table"]}>
      <QueryClientProvider client={queryClient}>
        <AdminTrendsPanel group="usage" />
      </QueryClientProvider>
    </MemoryRouter>,
  );
  await waitFor(() =>
    expect(api.getAdminTrends).toHaveBeenCalledWith(
      expect.objectContaining({ range: "7d" }),
    ),
  );
  await browser.click(screen.getByRole("button", { name: "Last 30 days" }));
  await waitFor(() =>
    expect(api.getAdminTrends).toHaveBeenCalledWith(
      expect.objectContaining({ range: "30d" }),
    ),
  );
});
