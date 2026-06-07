// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

// Mock the useAuth hook
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    error: null,
    isEarlyAccess: false,
    isReady: true,
    refresh: vi.fn(),
    updatePushoverToken: vi.fn(),
    signOut: vi.fn(),
    isAuth0Mode: false,
    loginWithAuth0: vi.fn(),
    auth0IsLoading: false,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => children,
}));

// Mock the auth0-react module to avoid import errors
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    isAuthenticated: false,
    isLoading: false,
    user: null,
    loginWithRedirect: vi.fn(),
    logout: vi.fn(),
    getAccessTokenSilently: vi.fn(),
  }),
  Auth0Provider: ({ children }: { children: ReactNode }) => children,
}));

describe("App", () => {
  it("renders the navigation header", () => {
    renderWithProviders(<App />);
    // The heading should contain "camply"
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
  });

  it("renders the home page search area", () => {
    renderWithProviders(<App />);
    // The search input should be present on the home page
    const searchInput = screen.queryByPlaceholderText(/search/i);
    const searchButton = screen.queryByRole("button", { name: /search/i });
    expect(searchInput || searchButton).toBeTruthy();
  });

  it("renders without crashing", () => {
    renderWithProviders(<App />);
    expect(document.body).toBeTruthy();
  });
});
