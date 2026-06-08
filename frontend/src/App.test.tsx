import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

Object.defineProperty(globalThis, "fetch", {
  value: vi.fn(),
  writable: true,
});

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

describe("App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.scrollTo = vi.fn();
    // Mock health check for all tests
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      json: async () => ({ status: 200, timestamp: "2024-01-01T00:00:00Z" }),
    });
  });

  it("renders the hero heading", () => {
    renderWithProviders();

    const heroHeading = screen.getByRole("heading", { level: 1 });
    expect(heroHeading).toBeInTheDocument();
    expect(heroHeading.textContent).toContain("Find Campsites at");
    expect(heroHeading.textContent).toContain("Campgrounds");
  });

  it("renders the footer brand", () => {
    renderWithProviders();

    // The footer contains "camply" text
    const camplyElements = screen.getAllByText("camply");
    expect(camplyElements.length).toBeGreaterThan(0);
  });

  it("renders the features section", () => {
    renderWithProviders();

    expect(screen.getByText("Why Choose camply?")).toBeInTheDocument();
  });

  it("renders the How It Works section", () => {
    renderWithProviders();

    const howItWorksHeadings = screen.getAllByRole("heading", {
      level: 2,
    });
    const howItWorks = howItWorksHeadings.find(
      (h) => h.textContent === "How It Works",
    );
    expect(howItWorks).toBeInTheDocument();
  });

  it("renders the CTA section", () => {
    renderWithProviders();

    const getStartedButtons = screen.getAllByText("Get Started");
    expect(getStartedButtons.length).toBeGreaterThan(0);
  });

  it("renders the development banner", () => {
    renderWithProviders();

    expect(
      screen.getByText(/camply is currently in development/i),
    ).toBeInTheDocument();
  });
});
