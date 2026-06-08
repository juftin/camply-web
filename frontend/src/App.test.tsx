import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
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
  it("renders the hero heading", async () => {
    renderWithProviders();

    const heroHeading = await screen.findByRole("heading", { level: 1 });
    expect(heroHeading).toBeInTheDocument();
    expect(heroHeading.textContent).toContain("Find Campsites at");
    expect(heroHeading.textContent).toContain("Campgrounds");
  });

  it("renders the footer brand", async () => {
    renderWithProviders();

    const camplyElements = await screen.findAllByText("camply");
    expect(camplyElements.length).toBeGreaterThan(0);
  });

  it("renders the features section", async () => {
    renderWithProviders();

    expect(
      await screen.findByText("Why Choose camply?"),
    ).toBeInTheDocument();
  });

  it("renders the How It Works section", async () => {
    renderWithProviders();

    const howItWorksHeadings = await screen.findAllByRole("heading", {
      level: 2,
    });
    const howItWorks = howItWorksHeadings.find(
      (h) => h.textContent === "How It Works",
    );
    expect(howItWorks).toBeInTheDocument();
  });

  it("renders the CTA section", async () => {
    renderWithProviders();

    const getStartedButtons = await screen.findAllByText("Get Started");
    expect(getStartedButtons.length).toBeGreaterThan(0);
  });

  it("renders the development banner", async () => {
    renderWithProviders();

    expect(
      await screen.findByText(/camply is currently in development/i),
    ).toBeInTheDocument();
  });
});
