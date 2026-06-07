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

// Mock API config to return synchronously so the loading state resolves
// immediately on the first render.
vi.mock("@/lib/api", () => ({
  fetchAuthConfig: vi.fn(() =>
    Promise.resolve({
      auth_mode: "local" as const,
      auth0_domain: null,
      auth0_client_id: null,
    }),
  ),
  setAccessTokenProvider: vi.fn(),
  getApiErrorMessage: vi.fn().mockReturnValue(""),
}));

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
    login: vi.fn(),
    authMode: "local" as const,
  }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  AuthModeContext: {
    Provider: ({ children }: { children: ReactNode }) => <>{children}</>,
  },
}));

describe("App", () => {
  it("renders without crashing", () => {
    renderWithProviders(<App />);
    expect(document.body).toBeTruthy();
  });
});
