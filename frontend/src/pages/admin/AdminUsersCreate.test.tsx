import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminUsers } from "./AdminUsers";
import { AuthConfigContext, AuthProvider } from "@/hooks/useAuth";
import * as api from "@/lib/api";
import type { AdminUserItem, AdminUserDetailResponse } from "@/lib/structs";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  listAdminUsers: vi.fn(),
  createAdminUser: vi.fn(),
  updateAdminUser: vi.fn(),
  getMe: vi.fn(),
}));

const existingUser: AdminUserItem = {
  id: "admin-1",
  email: "admin@example.test",
  is_admin: true,
  is_invited: true,
  scanning_enabled: true,
  has_pushover_token: false,
  total_scans: 0,
  active_scans: 0,
  created_at: "2026-10-10T12:00:00Z",
  must_change_password: false,
};

describe("AdminUsers Create User Dialog", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.mocked(api.listAdminUsers).mockResolvedValue({
      users: [existingUser],
      total: 1,
    });
    vi.mocked(api.getMe).mockResolvedValue({
      id: existingUser.id,
      email: existingUser.email,
      is_admin: true,
      is_invited: true,
      scanning_enabled: true,
      pushover_token: null,
    });
  });

  function setup() {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
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
              <AdminUsers />
            </AuthProvider>
          </AuthConfigContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    return userEvent.setup();
  }

  it("renders Create User button when session auth is active", async () => {
    setup();
    expect(
      await screen.findByRole("button", { name: /Create User/i }),
    ).toBeInTheDocument();
  });

  it("opens modal and creates a user with forced password change successfully", async () => {
    const createdResponse: AdminUserDetailResponse = {
      id: "new-user-id",
      email: "newperson@example.com",
      is_admin: false,
      is_invited: true,
      scanning_enabled: true,
      has_pushover_token: false,
      created_at: "2026-10-13T12:00:00Z",
      updated_at: "2026-10-13T12:00:00Z",
      total_scans: 0,
      active_scans: 0,
      must_change_password: true,
    };
    vi.mocked(api.createAdminUser).mockResolvedValue(createdResponse);

    const user = setup();
    await user.click(
      await screen.findByRole("button", { name: /Create User/i }),
    );

    expect(
      screen.getByRole("heading", { name: "Create User" }),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^Email/i), "newperson@example.com");
    await user.type(
      screen.getByLabelText(/Initial Password/i),
      "temp-secret-123",
    );

    // The submit button in the dialog footer
    const submitBtn = screen.getByRole("button", { name: "Create User" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(api.createAdminUser).toHaveBeenCalledWith({
        email: "newperson@example.com",
        password: "temp-secret-123",
        is_admin: false,
        is_invited: true,
        scanning_enabled: true,
        must_change_password: true,
      });
    });

    expect(
      await screen.findByText(
        /User newperson@example.com created successfully/i,
      ),
    ).toBeInTheDocument();
  });

  it("displays server error message when creation fails", async () => {
    vi.mocked(api.createAdminUser).mockRejectedValue(
      new Error("User with this email already exists"),
    );

    const user = setup();
    await user.click(
      await screen.findByRole("button", { name: /Create User/i }),
    );

    await user.type(screen.getByLabelText(/^Email/i), "admin@example.test");
    await user.type(
      screen.getByLabelText(/Initial Password/i),
      "duplicate-pass",
    );

    const submitBtn = screen.getByRole("button", { name: "Create User" });
    await user.click(submitBtn);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "User with this email already exists",
    );
    expect(
      screen.getByRole("heading", { name: "Create User" }),
    ).toBeInTheDocument();
  });

  it.each(["cancel", "escape"])(
    "discards the generated password on %s",
    async (method) => {
      const user = setup();
      await user.click(
        await screen.findByRole("button", { name: /Create User/i }),
      );

      expect(
        screen.getByRole("heading", { name: "Create User" }),
      ).toBeInTheDocument();
      await user.click(
        screen.getByRole("button", { name: "Generate Password" }),
      );

      if (method === "cancel") {
        await user.click(screen.getByRole("button", { name: "Cancel" }));
      } else {
        await user.keyboard("{Escape}");
      }

      await waitFor(() => {
        expect(
          screen.queryByRole("heading", { name: "Create User" }),
        ).not.toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: "Create User" }));
      expect(screen.getByLabelText("Initial Password")).toHaveValue("");
      expect(screen.getByLabelText("Initial Password")).toHaveAttribute(
        "type",
        "password",
      );
      expect(
        screen.queryByRole("button", { name: "Copy password" }),
      ).not.toBeInTheDocument();
    },
  );

  it("submits a generated password and clears it after creating the user", async () => {
    vi.mocked(api.createAdminUser).mockResolvedValue({
      ...existingUser,
      updated_at: "2026-10-13T12:00:00Z",
    });
    const user = setup();
    await user.click(
      await screen.findByRole("button", { name: "Create User" }),
    );
    await user.type(screen.getByLabelText("Email"), "generated@example.test");
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const password = (
      screen.getByLabelText("Initial Password") as HTMLInputElement
    ).value;
    expect(password).toHaveLength(24);
    expect(api.createAdminUser).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Create User" }));
    await waitFor(() =>
      expect(api.createAdminUser).toHaveBeenCalledWith(
        expect.objectContaining({ password }),
      ),
    );
    await screen.findByText(/created successfully/);
    expect(screen.queryByDisplayValue(password)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create User" }));
    expect(screen.getByLabelText("Initial Password")).toHaveValue("");
    expect(
      screen.queryByRole("button", { name: "Copy password" }),
    ).not.toBeInTheDocument();
  });
});

describe("AdminUsers Reset Password Dialog", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.mocked(api.listAdminUsers).mockResolvedValue({
      users: [existingUser],
      total: 1,
    });
    vi.mocked(api.getMe).mockResolvedValue({
      id: "admin-me",
      email: "me@example.test",
      is_admin: true,
      is_invited: true,
      scanning_enabled: true,
      pushover_token: null,
    });
  });

  function setup() {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
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
              <AdminUsers />
            </AuthProvider>
          </AuthConfigContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    return userEvent.setup();
  }

  it("submits a generated temporary password and clears it when reopening the dialog", async () => {
    vi.mocked(api.updateAdminUser).mockResolvedValue({
      ...existingUser,
      updated_at: "2026-10-13T12:00:00Z",
      must_change_password: true,
    });
    const user = setup();
    const resetButton = await screen.findByRole("button", {
      name: `Reset password for ${existingUser.email}`,
    });
    await user.click(resetButton);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    const password = (
      screen.getByLabelText("New Temporary Password") as HTMLInputElement
    ).value;
    expect(api.updateAdminUser).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Reset Password" }));
    await waitFor(() =>
      expect(api.updateAdminUser).toHaveBeenCalledWith(existingUser.id, {
        password,
        must_change_password: true,
      }),
    );
    await screen.findByText(/Temporary password set/);
    expect(screen.queryByDisplayValue(password)).not.toBeInTheDocument();
    await user.click(resetButton);
    expect(screen.getByLabelText("New Temporary Password")).toHaveValue("");
    expect(
      screen.queryByRole("button", { name: "Copy password" }),
    ).not.toBeInTheDocument();
  });

  it("discards a generated password when cancelling a row reset", async () => {
    const user = setup();
    const resetButton = await screen.findByRole("button", {
      name: `Reset password for ${existingUser.email}`,
    });
    await user.click(resetButton);
    await user.click(screen.getByRole("button", { name: "Generate Password" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(resetButton);
    expect(screen.getByLabelText("New Temporary Password")).toHaveValue("");
    expect(
      screen.queryByRole("button", { name: "Copy password" }),
    ).not.toBeInTheDocument();
  });

  it("opens reset modal from row action and resets user password with forced change", async () => {
    vi.mocked(api.updateAdminUser).mockResolvedValue({
      ...existingUser,
      updated_at: "2026-10-13T12:00:00Z",
      must_change_password: true,
    });

    const user = setup();
    const resetBtn = await screen.findByRole("button", {
      name: `Reset password for ${existingUser.email}`,
    });
    await user.click(resetBtn);

    expect(
      screen.getByRole("heading", { name: "Reset Password" }),
    ).toBeInTheDocument();

    const input = screen.getByLabelText(/New Temporary Password/i);
    await user.type(input, "new-temp-pw-999");

    const submitBtn = screen.getByRole("button", { name: "Reset Password" });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(api.updateAdminUser).toHaveBeenCalledWith(existingUser.id, {
        password: "new-temp-pw-999",
        must_change_password: true,
      });
    });

    expect(
      await screen.findByText(
        new RegExp(`Temporary password set for ${existingUser.email}`, "i"),
      ),
    ).toBeInTheDocument();
  });

  it("displays error when reset fails", async () => {
    vi.mocked(api.updateAdminUser).mockRejectedValue(
      new Error("Failed to reset password"),
    );

    const user = setup();
    const resetBtn = await screen.findByRole("button", {
      name: `Reset password for ${existingUser.email}`,
    });
    await user.click(resetBtn);

    const input = screen.getByLabelText(/New Temporary Password/i);
    await user.type(input, "fail-pw");

    const submitBtn = screen.getByRole("button", { name: "Reset Password" });
    await user.click(submitBtn);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed to reset password",
    );
    expect(
      screen.getByRole("heading", { name: "Reset Password" }),
    ).toBeInTheDocument();
  });
});
