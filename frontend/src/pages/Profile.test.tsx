// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { type ReactElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { Profile } from "./Profile";

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

// Mock the useAuth hook
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "test-uuid",
      email: "test@camply.local",
      is_early_access_user: true,
      pushover_token: null,
    },
    isLoading: false,
    error: null,
    isEarlyAccess: true,
    isReady: true,
    refresh: vi.fn(),
    updatePushoverToken: vi.fn(),
    signOut: vi.fn(),
    isAuth0Mode: false,
    loginWithAuth0: vi.fn(),
    auth0IsLoading: false,
  }),
}));

describe("Profile", () => {
  it("renders the profile heading", () => {
    renderWithProviders(<Profile />);
    expect(screen.getByText("Profile")).toBeInTheDocument();
  });

  it("shows the user email", () => {
    renderWithProviders(<Profile />);
    expect(screen.getByText("test@camply.local")).toBeInTheDocument();
  });

  it("shows the early access badge", () => {
    renderWithProviders(<Profile />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders the pushover settings section", () => {
    renderWithProviders(<Profile />);
    expect(screen.getByText("Notifications")).toBeInTheDocument();
  });

  it("renders the sign out section", () => {
    renderWithProviders(<Profile />);
    expect(screen.getByText("Sign Out")).toBeInTheDocument();
  });
});
