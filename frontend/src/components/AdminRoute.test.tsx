import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AuthState } from "@/hooks/useAuth";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AdminRoute } from "./AdminRoute";

let mockAuthState: AuthState;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

function renderAdminRoute() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminRoute>
          <div data-testid="admin-content">Admin Protected Content</div>
        </AdminRoute>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AdminRoute", () => {
  it("renders loading state when auth is not ready", () => {
    mockAuthState = {
      user: null,
      isLoading: true,
      error: null,
      isInvited: false,
      isAdmin: false,
      isScanningEnabled: true,
      isReady: false,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "session",
      inviteOnly: false,
      autoLogin: false,
      signupEnabled: false,
      accountPath: "/dashboard",
    };

    renderAdminRoute();
    expect(screen.queryByTestId("admin-content")).not.toBeInTheDocument();
  });

  it("denies access to non-admin users", () => {
    mockAuthState = {
      user: {
        id: "user-123",
        email: "user@example.com",
        is_invited: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
      },
      isLoading: false,
      error: null,
      isInvited: true,
      isAdmin: false,
      isScanningEnabled: true,
      isReady: true,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "session",
      inviteOnly: false,
      autoLogin: false,
      signupEnabled: false,
      accountPath: "/dashboard",
    };

    renderAdminRoute();
    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(
      screen.getByText(/Administrator privileges are required/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("admin-content")).not.toBeInTheDocument();
  });

  it("renders protected content for admin users", () => {
    mockAuthState = {
      user: {
        id: "admin-123",
        email: "admin@example.com",
        is_invited: true,
        is_admin: true,
        scanning_enabled: true,
        pushover_token: null,
      },
      isLoading: false,
      error: null,
      isInvited: true,
      isAdmin: true,
      isScanningEnabled: true,
      isReady: true,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "session",
      inviteOnly: false,
      autoLogin: false,
      signupEnabled: false,
      accountPath: "/dashboard",
    };

    renderAdminRoute();
    expect(screen.getByTestId("admin-content")).toBeInTheDocument();
    expect(screen.queryByText("Access Denied")).not.toBeInTheDocument();
  });

  it("renders change password required when user must change password", () => {
    mockAuthState = {
      user: {
        id: "admin-123",
        email: "admin@example.com",
        is_invited: true,
        is_admin: true,
        scanning_enabled: true,
        pushover_token: null,
        must_change_password: true,
      },
      isLoading: false,
      error: null,
      isInvited: true,
      isAdmin: true,
      isScanningEnabled: true,
      isReady: true,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "session",
      inviteOnly: false,
      autoLogin: false,
      signupEnabled: false,
      accountPath: "/dashboard",
    };

    renderAdminRoute();
    expect(screen.getByText("Password Change Required")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-content")).not.toBeInTheDocument();
  });
});
