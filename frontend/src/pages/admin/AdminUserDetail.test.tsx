import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminUserDetail } from "./AdminUserDetail";
import { AuthConfigContext, AuthProvider } from "@/hooks/useAuth";
import * as api from "@/lib/api";
import type {
  AdminUserDetailResponse,
  AdminScanListResponse,
} from "@/lib/structs";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  getAdminUser: vi.fn(),
  updateAdminUser: vi.fn(),
  listAdminScans: vi.fn(),
  getMe: vi.fn(),
}));

const loggedInAdmin = {
  id: "admin-current-id",
  email: "current_admin@example.com",
  is_admin: true,
  is_invited: true,
  scanning_enabled: true,
  pushover_token: null,
};

const otherUser: AdminUserDetailResponse = {
  id: "other-user-id",
  email: "target_user@example.com",
  is_admin: false,
  is_invited: true,
  scanning_enabled: true,
  has_pushover_token: false,
  created_at: "2026-10-10T12:00:00Z",
  updated_at: "2026-10-10T12:00:00Z",
  total_scans: 0,
  active_scans: 0,
  must_change_password: false,
};

const emptyScans: AdminScanListResponse = {
  scans: [],
  total: 0,
};

describe("AdminUserDetail Permissions", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.mocked(api.getMe).mockResolvedValue(loggedInAdmin);
    vi.mocked(api.getAdminUser).mockResolvedValue(otherUser);
    vi.mocked(api.listAdminScans).mockResolvedValue(emptyScans);
  });

  function setup(userId = otherUser.id) {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/admin/users/${userId}`]}>
          <AuthConfigContext.Provider
            value={{
              auth_mode: "session",
              auto_login: false,
              invite_only: false,
              signup_enabled: false,
              auth0_domain: null,
              auth0_client_id: null,
              auth0_audience: null,
            }}
          >
            <AuthProvider>
              <Routes>
                <Route
                  path="/admin/users/:userId"
                  element={<AdminUserDetail />}
                />
              </Routes>
            </AuthProvider>
          </AuthConfigContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    return userEvent.setup();
  }

  it("allows promoting a standard user to administrator", async () => {
    const user = setup();
    expect(
      await screen.findByRole("heading", { name: /target_user@example.com/i }),
    ).toBeInTheDocument();

    const adminSwitch = screen.getByRole("switch", {
      name: `Administrator privileges for ${otherUser.email}`,
    });
    expect(adminSwitch).not.toBeChecked();

    vi.mocked(api.updateAdminUser).mockResolvedValue({
      ...otherUser,
      is_admin: true,
    });

    await user.click(adminSwitch);

    await waitFor(() => {
      expect(api.updateAdminUser).toHaveBeenCalledWith(otherUser.id, {
        is_admin: true,
      });
    });

    expect(
      await screen.findByText(
        /Administrator privileges granted to target_user@example.com/i,
      ),
    ).toBeInTheDocument();
  });

  it("disables administrator switch when viewing one's own account", async () => {
    vi.mocked(api.getAdminUser).mockResolvedValue({
      ...otherUser,
      id: loggedInAdmin.id,
      email: loggedInAdmin.email,
      is_admin: true,
    });

    setup(loggedInAdmin.id);

    expect(
      await screen.findByRole("heading", {
        name: /current_admin@example.com/i,
      }),
    ).toBeInTheDocument();

    const adminSwitch = screen.getByRole("switch", {
      name: `Administrator privileges for ${loggedInAdmin.email}`,
    });
    expect(adminSwitch).toBeChecked();
    expect(adminSwitch).toBeDisabled();

    expect(
      screen.getByText("You cannot remove your own administrator privileges"),
    ).toBeInTheDocument();
  });

  it("displays error message if promotion fails", async () => {
    vi.mocked(api.updateAdminUser).mockRejectedValue(
      new Error("Failed to update role on server"),
    );

    const user = setup();
    const adminSwitch = await screen.findByRole("switch", {
      name: `Administrator privileges for ${otherUser.email}`,
    });

    await user.click(adminSwitch);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to update role on server",
    );
  });

  it("allows an administrator to reset a user password, forcing rotation on next login", async () => {
    vi.mocked(api.updateAdminUser).mockResolvedValue({
      ...otherUser,
      must_change_password: true,
    });

    const user = setup();
    const resetBtn = await screen.findByRole("button", {
      name: /Reset Password/i,
    });
    await user.click(resetBtn);

    expect(
      screen.getByRole("heading", { name: "Reset Password" }),
    ).toBeInTheDocument();

    const input = screen.getByLabelText(/New Temporary Password/i);
    await user.type(input, "TemporaryPass456!");

    const submitBtn = screen.getByRole("button", { name: "Reset Password" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(api.updateAdminUser).toHaveBeenCalledWith(otherUser.id, {
        password: "TemporaryPass456!",
        must_change_password: true,
      });
    });

    expect(
      await screen.findByText(
        new RegExp(`Temporary password set for ${otherUser.email}`, "i"),
      ),
    ).toBeInTheDocument();
  });

  it("displays error in dialog if password reset fails", async () => {
    vi.mocked(api.updateAdminUser).mockRejectedValue(
      new Error("Password does not meet complexity requirements"),
    );

    const user = setup();
    const resetBtn = await screen.findByRole("button", {
      name: /Reset Password/i,
    });
    await user.click(resetBtn);

    const input = screen.getByLabelText(/New Temporary Password/i);
    await user.type(input, "short");

    const submitBtn = screen.getByRole("button", { name: "Reset Password" });
    await user.click(submitBtn);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password does not meet complexity requirements",
    );
    expect(
      screen.getByRole("heading", { name: "Reset Password" }),
    ).toBeInTheDocument();
  });
});
