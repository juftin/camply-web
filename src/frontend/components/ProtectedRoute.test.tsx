import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { AuthState } from "@/hooks/useAuth";
import { ProtectedRoute } from "./ProtectedRoute";

let mockAuthState: Partial<AuthState>;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

function renderProtectedRoute(requireInvite = false) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireInvite={requireInvite}>
                <div data-testid="protected-content">Protected Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/auth" element={<div>Auth Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("renders loading state when auth is not ready", () => {
    mockAuthState = {
      isLoading: true,
      isReady: false,
      user: null,
      error: null,
    };
    renderProtectedRoute();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading your account…",
    );
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("renders error state when auth has an error", () => {
    mockAuthState = {
      isLoading: false,
      isReady: true,
      user: null,
      error: "Authentication failed",
    };
    renderProtectedRoute();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Authentication failed",
    );
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("redirects to /auth when user is not authenticated", () => {
    mockAuthState = {
      isLoading: false,
      isReady: true,
      user: null,
      error: null,
    };
    renderProtectedRoute();
    expect(screen.getByText("Auth Page")).toBeInTheDocument();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("renders change password required when must_change_password is true", () => {
    mockAuthState = {
      isLoading: false,
      isReady: true,
      user: {
        id: "user-1",
        email: "user@example.com",
        is_invited: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        must_change_password: true,
      },
      error: null,
    };
    renderProtectedRoute();
    expect(screen.getByText("Password Change Required")).toBeInTheDocument();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated and no password change is required", () => {
    mockAuthState = {
      isLoading: false,
      isReady: true,
      user: {
        id: "user-1",
        email: "user@example.com",
        is_invited: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        must_change_password: false,
      },
      error: null,
    };
    renderProtectedRoute();
    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
  });
});
