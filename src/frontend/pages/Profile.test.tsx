import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import type { AuthState } from "@/hooks/useAuth";
import { Profile } from "./Profile";
import { updateMe } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  updateMe: vi.fn().mockResolvedValue({}),
  sendTestNotification: vi
    .fn()
    .mockResolvedValue({ status: "sent", provider: "ntfy" }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

let mockAuthState: AuthState;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
  AuthProvider: ({ children }: { children: ReactNode }) => children,
  AuthConfigContext: {
    Provider: ({ children }: { children: ReactNode }) => children,
  },
}));

function renderProfile(overrides: Partial<AuthState> = {}) {
  mockAuthState = {
    user: {
      id: "test-user-id",
      email: "test@example.com",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: "existing-token",
    },
    isLoading: false,
    error: null,
    isInvited: true,
    isAdmin: false,
    isScanningEnabled: true,
    isReady: true,
    refresh: vi.fn(),
    updatePushoverToken: vi.fn().mockResolvedValue(undefined),
    signOut: vi.fn(),
    login: vi.fn(),
    authMode: "session",
    inviteOnly: false,
    autoLogin: false,
    signupEnabled: false,
    accountPath: "/dashboard",
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
  vi.clearAllMocks();
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

  it("shows dashboard link when user is invited", () => {
    renderProfile();
    expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
  });

  it("shows dashboard link even when user is not invited", () => {
    renderProfile({
      user: {
        id: "test-user-id",
        email: "test@example.com",
        is_invited: false,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
      },
      isInvited: false,
    });
    expect(screen.getByText("Go to Dashboard")).toBeInTheDocument();
  });

  it("calls signOut when sign out button is clicked", () => {
    const signOut = vi.fn();
    renderProfile({ signOut });
    fireEvent.click(screen.getByText("Sign Out"));
    expect(signOut).toHaveBeenCalledOnce();
  });

  it("saves Pushover preferences together when save is clicked", async () => {
    renderProfile();
    const input = screen.getByPlaceholderText("Enter your Pushover user key");
    fireEvent.change(input, { target: { value: "new-token" } });
    fireEvent.click(screen.getByText("Save notification settings"));
    await waitFor(() => {
      expect(updateMe).toHaveBeenCalledWith({
        notification_provider: "pushover",
        pushover_token: "new-token",
      });
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

it("hides sign-out during automatic local login", () => {
  renderProfile({ autoLogin: true });
  expect(
    screen.queryByRole("button", { name: "Sign Out" }),
  ).not.toBeInTheDocument();
});

it("immediately switches provider fields and saves an editable user ID topic", async () => {
  renderProfile({
    user: {
      id: "1234567a-abcd-1234-1234-123456789abc",
      email: "test@example.test",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: "saved-key",
      notification_provider: "pushover",
      ntfy_topic: null,
      ntfy_subscription_url: "https://ntfy.sh",
    },
  });
  expect(screen.getAllByLabelText("Pushover User Key")).toHaveLength(1);
  expect(screen.queryByLabelText("Your ntfy topic")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Notification provider"), {
    target: { value: "ntfy" },
  });
  expect(screen.queryByLabelText("Pushover User Key")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Your ntfy topic")).toHaveValue(
    "camply-1234567",
  );
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "" },
  });
  expect(screen.getByText("Save notification settings")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Your ntfy topic"), {
    target: { value: "edited-topic" },
  });
  fireEvent.click(screen.getByText("Save notification settings"));
  await waitFor(() =>
    expect(updateMe).toHaveBeenLastCalledWith({
      notification_provider: "ntfy",
      ntfy_topic: "edited-topic",
      ntfy_server_url: "https://ntfy.sh",
      ntfy_access_token: null,
    }),
  );
  fireEvent.change(screen.getByLabelText("Notification provider"), {
    target: { value: "pushover" },
  });
  expect(screen.queryByLabelText("Your ntfy topic")).not.toBeInTheDocument();
  expect(screen.getAllByLabelText("Pushover User Key")).toHaveLength(1);
  fireEvent.change(screen.getByLabelText("Pushover User Key"), {
    target: { value: "new-key" },
  });
  fireEvent.click(screen.getByText("Save notification settings"));
  await waitFor(() =>
    expect(updateMe).toHaveBeenLastCalledWith({
      notification_provider: "pushover",
      pushover_token: "new-key",
    }),
  );
});
