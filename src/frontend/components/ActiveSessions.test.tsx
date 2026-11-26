import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthState } from "@/hooks/useAuth";
import { listMySessions, revokeMySession } from "@/lib/api";
import type { UserSessionItem } from "@/lib/structs";
import { formatSessionDevice } from "@/lib/utils";
import { ActiveSessions } from "./ActiveSessions";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    listMySessions: vi.fn(),
    revokeMySession: vi.fn(),
  };
});

let mockAuthState: AuthState;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

const currentSession: UserSessionItem = {
  id: "session-current",
  user_agent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
  ip_address: "198.51.100.10",
  created_at: "2026-11-15T10:00:00Z",
  expires_at: "2026-11-22T10:00:00Z",
  is_current: true,
};

const otherSession: UserSessionItem = {
  id: "session-other",
  user_agent: null,
  ip_address: null,
  created_at: "2026-11-14T08:30:00Z",
  expires_at: "2026-11-21T08:30:00Z",
  is_current: false,
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retryDelay: 0 },
    },
  });
}

function renderActiveSessions(
  overrides: Partial<AuthState> = {},
  queryClient = createTestQueryClient(),
) {
  mockAuthState = {
    user: {
      id: "user-1",
      email: "camper@example.test",
      is_invited: true,
      is_admin: false,
      scanning_enabled: true,
      pushover_token: null,
      must_change_password: false,
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

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/profile"]}>
          <Routes>
            <Route path="/profile" element={<ActiveSessions />} />
            <Route path="/auth" element={<div>Sign In Page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("formatSessionDevice", () => {
  it("formats known browsers and platforms and falls back gracefully", () => {
    expect(formatSessionDevice(null)).toBe("Unknown device");
    expect(formatSessionDevice("   ")).toBe("Unknown device");
    expect(formatSessionDevice(currentSession.user_agent)).toBe(
      "Chrome on macOS",
    );
    expect(
      formatSessionDevice(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
      ),
    ).toBe("Safari on iPhone");
    expect(
      formatSessionDevice(
        "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
      ),
    ).toBe("Firefox on Linux");
    expect(
      formatSessionDevice(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
      ),
    ).toBe("Microsoft Edge on Windows");
    expect(formatSessionDevice("CustomAgent/2.0")).toBe("CustomAgent/2.0");
  });
});

describe("ActiveSessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render or fetch outside interactive password session mode", () => {
    renderActiveSessions({ authMode: "auth0" });
    expect(screen.queryByText("Active Sessions")).not.toBeInTheDocument();

    renderActiveSessions({ authMode: "session", autoLogin: true });
    expect(screen.queryByText("Active Sessions")).not.toBeInTheDocument();

    renderActiveSessions({
      authMode: "session",
      user: {
        id: "user-1",
        email: "camper@example.test",
        is_invited: true,
        is_admin: false,
        scanning_enabled: true,
        pushover_token: null,
        must_change_password: true,
      },
    });
    expect(screen.queryByText("Active Sessions")).not.toBeInTheDocument();
    expect(listMySessions).not.toHaveBeenCalled();
  });

  it("renders session metadata, current badge, and fallback device label", async () => {
    vi.mocked(listMySessions).mockResolvedValue({
      items: [currentSession, otherSession],
    });

    renderActiveSessions();

    expect(await screen.findByText("Chrome on macOS")).toBeInTheDocument();
    expect(screen.getByText("Unknown device")).toHaveClass("break-words");
    expect(screen.getByText("Current")).toBeInTheDocument();
    expect(screen.getByText("IP 198.51.100.10")).toBeInTheDocument();
    expect(
      screen.getByText(
        `Signed in ${new Date(currentSession.created_at).toLocaleString()}`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `Expires ${new Date(currentSession.expires_at).toLocaleString()}`,
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Revoke" })).toHaveLength(2);
  });

  it("revokes another session, disables only its button while pending, and refreshes the list", async () => {
    const user = userEvent.setup();
    vi.mocked(listMySessions)
      .mockResolvedValueOnce({ items: [currentSession, otherSession] })
      .mockResolvedValueOnce({ items: [currentSession] });

    let resolveRevoke: () => void = () => {};
    vi.mocked(revokeMySession).mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveRevoke = resolve;
        }),
    );

    renderActiveSessions();

    const unknownItem = (await screen.findByText("Unknown device")).closest(
      "li",
    )!;
    const currentItem = screen.getByText("Chrome on macOS").closest("li")!;

    await user.click(
      within(unknownItem).getByRole("button", { name: "Revoke" }),
    );

    expect(
      within(unknownItem).getByRole("button", { name: "Revoking…" }),
    ).toBeDisabled();
    expect(
      within(currentItem).getByRole("button", { name: "Revoke" }),
    ).toBeEnabled();

    resolveRevoke();

    await waitFor(() => {
      expect(revokeMySession).toHaveBeenCalledWith("session-other");
      expect(screen.queryByText("Unknown device")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent("Session revoked.");
  });

  it("revokes the current session, clears caches, and navigates cleanly to /auth", async () => {
    const user = userEvent.setup();
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(["me"], { id: "user-1" });
    queryClient.setQueryData(["scans"], { scans: [], total: 0 });
    vi.mocked(listMySessions).mockResolvedValue({
      items: [currentSession, otherSession],
    });
    vi.mocked(revokeMySession).mockResolvedValue(undefined);

    renderActiveSessions({}, queryClient);

    const currentItem = (await screen.findByText("Chrome on macOS")).closest(
      "li",
    )!;
    await user.click(
      within(currentItem).getByRole("button", { name: "Revoke" }),
    );

    await waitFor(() => {
      expect(revokeMySession).toHaveBeenCalledWith("session-current");
      expect(screen.getByText("Sign In Page")).toBeInTheDocument();
    });

    expect(queryClient.getQueryData(["me"])).toBeNull();
    expect(queryClient.getQueryData(["scans"])).toBeUndefined();
    expect(queryClient.getQueryData(["me", "sessions"])).toBeUndefined();
  });

  it("displays an error when loading sessions fails", async () => {
    vi.mocked(listMySessions).mockRejectedValue(
      new Error("Could not load sessions"),
    );

    renderActiveSessions();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load sessions",
    );
  });

  it("displays an error and re-enables the button when revoking a session fails", async () => {
    const user = userEvent.setup();
    vi.mocked(listMySessions).mockResolvedValue({
      items: [currentSession, otherSession],
    });
    vi.mocked(revokeMySession).mockRejectedValueOnce(
      new Error("Session revocation failed"),
    );

    renderActiveSessions();
    const unknownItem = (await screen.findByText("Unknown device")).closest(
      "li",
    )!;
    await user.click(
      within(unknownItem).getByRole("button", { name: "Revoke" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Session revocation failed",
    );
    expect(
      within(unknownItem).getByRole("button", { name: "Revoke" }),
    ).toBeEnabled();
  });
});
