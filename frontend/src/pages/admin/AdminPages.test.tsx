import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AdminOverview } from "./AdminOverview";
import { AdminUsers } from "./AdminUsers";
import { AdminScans } from "./AdminScans";
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
    getAdminOverview: vi.fn(),
    listAdminUsers: vi.fn(),
    listAdminScans: vi.fn(),
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
    group: "usage",
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

describe("AdminOverview", () => {
  it("renders overview metrics and alerts", async () => {
    vi.mocked(api.getAdminOverview).mockResolvedValue({
      total_users: 15,
      scanning_enabled_users: 12,
      suspended_users: 3,
      total_scans: 40,
      saved_active_scans: 35,
      eligible_scans: 28,
      unique_targets: 10,
      eligible_targets: 8,
      dormant_targets: 2,
      overdue_targets: 1,
      heartbeat_interval_seconds: 30,
      target_cooldown_seconds: 120,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminOverview />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("15")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("40")).toBeInTheDocument();
      expect(
        screen.getByText(/1 Target Overdue for Checking/i),
      ).toBeInTheDocument();
    });
  });
});

describe("AdminUsers", () => {
  it("renders user table with privileges and roles", async () => {
    vi.mocked(api.listAdminUsers).mockResolvedValue({
      users: [
        {
          id: "u-1",
          email: "alice@example.com",
          auth0_id: null,
          is_admin: true,
          is_early_access_user: true,
          scanning_enabled: true,
          has_pushover_token: true,
          total_scans: 5,
          active_scans: 3,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: "u-2",
          email: "bob@example.com",
          auth0_id: null,
          is_admin: false,
          is_early_access_user: true,
          scanning_enabled: false,
          has_pushover_token: false,
          total_scans: 2,
          active_scans: 0,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 2,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminUsers />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      expect(screen.getByText("Admin")).toBeInTheDocument();
      expect(screen.getAllByText("User").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Enabled").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Suspended").length).toBeGreaterThan(0);
    });
  });
});

describe("AdminScans", () => {
  it("renders cross-user scan fleet", async () => {
    vi.mocked(api.listAdminScans).mockResolvedValue({
      scans: [
        {
          id: "s-1",
          user_id: "u-1",
          user_email: "alice@example.com",
          target_id: "t-1",
          provider_id: 1,
          campground_id: "cg-1",
          campground_name: "Yosemite Pines",
          start_date: "2026-10-10",
          end_date: "2026-10-12",
          is_active: true,
          is_eligible: true,
          user_scanning_enabled: true,
          min_stay_length: 1,
          preferred_types: [],
          require_electric: false,
          last_checked_at: null,
          found_count: 2,
          created_at: new Date().toISOString(),
        },
      ],
      total: 1,
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminScans />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Yosemite Pines")).toBeInTheDocument();
      expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      expect(screen.getAllByText("Eligible").length).toBeGreaterThan(0);
    });
  });
});
