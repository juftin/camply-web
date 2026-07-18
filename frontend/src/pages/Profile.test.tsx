import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import type { AuthState } from "@/hooks/useAuth";
import { Profile } from "./Profile";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

let mockAuthState: AuthState;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
  AuthProvider: ({ children }: { children: ReactNode }) => children,
  AuthModeContext: { Provider: ({ children }: { children: ReactNode }) => children },
}));

function renderProfile(overrides: Partial<AuthState> = {}) {
  mockAuthState = {
    user: {
      id: "test-user-id",
      email: "test@example.com",
      is_early_access_user: true,
      pushover_token: "existing-token",
    },
    isLoading: false,
    error: null,
    isEarlyAccess: true,
    isReady: true,
    refresh: vi.fn(),
    updatePushoverToken: vi.fn().mockResolvedValue(undefined),
    signOut: vi.fn(),
    login: vi.fn(),
    authMode: "basic",
    ...overrides,
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  queryClient.clear();
});

describe("Profile", () => {
  it("renders the user's email", () => {
    renderProfile();
    expect(screen.getByDisplayValue("test@example.com")).toBeInTheDocument();
  });

  it("renders the pushover key input", () => {
    renderProfile();
    const input = screen.getByPlaceholderText("Enter your Pushover user key");
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue("existing-token");
  });

  it("shows dashboard link when user is early access", () => {
    renderProfile();
    expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
  });

  it("shows dashboard link even when user is not early access", () => {
    renderProfile({
      user: {
        id: "test-user-id",
        email: "test@example.com",
        is_early_access_user: false,
        pushover_token: null,
      },
      isEarlyAccess: false,
    });
    expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
  });

  it("calls signOut when sign out button is clicked", () => {
    const signOut = vi.fn();
    renderProfile({ signOut });
    fireEvent.click(screen.getByText("Sign Out"));
    expect(signOut).toHaveBeenCalledOnce();
  });

  it("calls updatePushoverToken when save is clicked", async () => {
    const updatePushoverToken = vi.fn().mockResolvedValue(undefined);
    renderProfile({ updatePushoverToken });
    const input = screen.getByPlaceholderText("Enter your Pushover user key");
    fireEvent.change(input, { target: { value: "new-token" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(updatePushoverToken).toHaveBeenCalledWith("new-token");
    });
  });

  it("shows loading state when isLoading is true", () => {
    renderProfile({ isLoading: true });
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("shows not signed in message when user is null", () => {
    renderProfile({ user: null, isLoading: false });
    expect(screen.getByText("Not signed in")).toBeInTheDocument();
  });
});
