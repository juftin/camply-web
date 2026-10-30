import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminUsers } from "./AdminUsers";
import { AdminTargetDetail } from "./AdminTargetDetail";
import { useAuth, AuthConfigContext, AuthProvider } from "@/hooks/useAuth";
import * as api from "@/lib/api";
import type { AdminUserItem, AdminTargetDetailResponse } from "@/lib/structs";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  listAdminUsers: vi.fn(),
  updateAdminUser: vi.fn(),
  getAdminTarget: vi.fn(),
  getMe: vi.fn(),
}));

const user: AdminUserItem = {
  id: "user-1",
  email: "camper@example.test",
  is_admin: true,
  is_invited: true,
  scanning_enabled: true,
  has_pushover_token: false,
  total_scans: 1,
  active_scans: 1,
  created_at: "2026-10-10T12:00:00Z",
  must_change_password: false,
};
const target: AdminTargetDetailResponse = {
  id: "target-1",
  provider_id: 1,
  campground_id: "cg-1",
  campground_name: "Test Campground",
  start_date: "2027-01-01",
  end_date: "2027-01-02",
  hash: "synthetic",
  created_at: user.created_at,
  total_subscribers: 51,
  eligible_subscribers: 1,
  subscribers_total: 51,
  overdue_threshold_seconds: 175,
  status: "active",
  subscribers: [],
};

/** Expose URL changes so navigation behavior is part of the assertion. */
function LocationProbe() {
  return <output data-testid="location">{useLocation().search}</output>;
}
/** Display cached profile state alongside admin controls. */
function ProfileProbe() {
  return (
    <output data-testid="profile">
      {String(useAuth().user?.scanning_enabled)}
    </output>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listAdminUsers).mockResolvedValue({ users: [user], total: 51 });
  vi.mocked(api.getAdminTarget).mockResolvedValue(target);
  vi.mocked(api.getMe).mockResolvedValue({
    id: user.id,
    email: user.email,
    is_admin: true,
    is_invited: true,
    scanning_enabled: true,
    pushover_token: null,
  });
});

/** Render real query hooks and URL state, mocking only HTTP transport functions. */
function setup(path = "/admin/users") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AuthConfigContext.Provider
          value={{
            auth_mode: "none",
            auto_login: true,
            invite_only: false,
            signup_enabled: false,
            auth0_domain: null,
            auth0_client_id: null,
            auth0_audience: null,
          }}
        >
          <AuthProvider>
            <AdminUsers />
            <ProfileProbe />
          </AuthProvider>
        </AuthConfigContext.Provider>
        <Routes>
          <Route
            path="/admin/targets/:targetId"
            element={<AdminTargetDetail />}
          />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

describe("Admin interactions", () => {
  it("shows suspension failures and preserves the displayed state", async () => {
    vi.mocked(api.updateAdminUser).mockRejectedValue(
      new Error("Synthetic save failure"),
    );
    const browser = setup();
    await browser.click(
      await screen.findByRole("switch", { name: /Scanning access/ }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Synthetic save failure",
    );
    expect(screen.getByRole("switch")).toBeChecked();
  });

  it("paginates and resets pagination when a search changes", async () => {
    const browser = setup("/admin/users?status=suspended&page=1");
    await screen.findByText(user.email);
    expect(api.listAdminUsers).toHaveBeenCalledWith(
      expect.objectContaining({ offset: 50, scanning_enabled: false }),
    );
    await browser.type(screen.getByPlaceholderText(/Search by email/), "camp");
    await waitFor(() =>
      expect(api.listAdminUsers).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 0, search: "camp" }),
      ),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("search=camp");
    expect(screen.getByTestId("location")).not.toHaveTextContent("page=");
    await browser.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("page=1"),
    );
  });

  it("refreshes target eligibility and the current profile after suspension", async () => {
    vi.mocked(api.updateAdminUser).mockImplementation(async () => {
      vi.mocked(api.getAdminTarget).mockResolvedValue({
        ...target,
        eligible_subscribers: 0,
        status: "dormant",
      });
      vi.mocked(api.getMe).mockResolvedValue({
        id: user.id,
        email: user.email,
        is_admin: true,
        is_invited: true,
        scanning_enabled: false,
        pushover_token: null,
      });
      vi.mocked(api.listAdminUsers).mockResolvedValue({
        users: [{ ...user, scanning_enabled: false }],
        total: 1,
      });
      return { ...user, updated_at: user.created_at };
    });
    const browser = setup("/admin/targets/target-1");
    expect(await screen.findByText("Eligible for checks")).toBeInTheDocument();
    await browser.click(
      await screen.findByRole("switch", { name: /Scanning access/ }),
    );
    expect(
      await screen.findByText("Dormant (no eligible scans)"),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("profile")).toHaveTextContent("false"),
    );
    expect(
      await screen.findByText(/Login and saved scans are preserved/),
    ).toBeInTheDocument();
  });
});
