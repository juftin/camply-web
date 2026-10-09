import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AuthState } from "@/hooks/useAuth";
import { AdminRoute } from "./AdminRoute";

let mockAuthState: AuthState;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

function renderAdminRoute() {
  return render(
    <MemoryRouter>
      <AdminRoute>
        <div data-testid="admin-content">Admin Protected Content</div>
      </AdminRoute>
    </MemoryRouter>,
  );
}

describe("AdminRoute", () => {
  it("renders loading state when auth is not ready", () => {
    mockAuthState = {
      user: null,
      isLoading: true,
      error: null,
      isEarlyAccess: false,
      isAdmin: false,
      isScanningEnabled: true,
      isReady: false,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "basic",
    };

    renderAdminRoute();
    expect(screen.queryByTestId("admin-content")).not.toBeInTheDocument();
  });

  it("denies access to non-admin users", () => {
    mockAuthState = {
      user: {
        id: "user-123",
        email: "user@example.com",
        is_early_access_user: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
      },
      isLoading: false,
      error: null,
      isEarlyAccess: true,
      isAdmin: false,
      isScanningEnabled: true,
      isReady: true,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "basic",
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
        is_early_access_user: true,
        is_admin: true,
        scanning_enabled: true,
        pushover_token: null,
      },
      isLoading: false,
      error: null,
      isEarlyAccess: true,
      isAdmin: true,
      isScanningEnabled: true,
      isReady: true,
      refresh: vi.fn(),
      updatePushoverToken: vi.fn(),
      signOut: vi.fn(),
      login: vi.fn(),
      authMode: "basic",
    };

    renderAdminRoute();
    expect(screen.getByTestId("admin-content")).toBeInTheDocument();
    expect(screen.queryByText("Access Denied")).not.toBeInTheDocument();
  });
});
