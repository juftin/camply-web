import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { Auth0Provider } from "@auth0/auth0-react";
import { AxiosError } from "axios";
import App from "./App";
import {
  fetchAuthConfig,
  getMe,
  submitAccessRequest,
  loginSession,
  logoutSession,
  listScans,
  getScan,
} from "@/lib/api";
import type { AuthConfig } from "@/lib/api";
import { useScans, useScanDetail } from "@/hooks/useScans";

const auth0 = vi.hoisted(() => ({
  isAuthenticated: false,
  isLoading: false,
  getAccessTokenSilently: vi.fn().mockResolvedValue("token"),
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("@auth0/auth0-react", () => ({
  Auth0Provider: vi.fn(({ children }: { children: ReactNode }) => children),
  useAuth0: () => auth0,
}));

vi.mock("@/lib/api", () => ({
  fetchAuthConfig: vi.fn(),
  getMe: vi.fn(),
  updateMe: vi.fn(),
  loginSession: vi.fn(),
  logoutSession: vi.fn(),
  listScans: vi.fn(),
  getScan: vi.fn(),
  submitAccessRequest: vi.fn(),
  setAccessTokenProvider: vi.fn(),
  getApiErrorMessage: vi.fn().mockReturnValue("Authentication failed"),
}));

// Keep authentication and scan queries real while mocking network requests.
vi.mock("@/pages/Dashboard", () => ({
  Dashboard: () => {
    useScans();
    return <div>Scan dashboard</div>;
  },
}));
vi.mock("@/pages/ScanDetail", () => ({
  ScanDetail: () => {
    useScanDetail("test");
    return <div>Scan detail</div>;
  },
}));
vi.mock("@/components/SearchBar", () => ({ SearchBar: () => null }));

const localConfig: AuthConfig = {
  auth_mode: "none",
  auth0_domain: null,
  auth0_client_id: null,
  auth0_audience: null,
  invite_only: false,
  auto_login: true,
  signup_enabled: false,
};
const auth0Config: AuthConfig = {
  ...localConfig,
  auto_login: false,
  auth_mode: "auth0",
  auth0_domain: "test.example.com",
  auth0_client_id: "test-client",
  auth0_audience: "https://api.example.com",
  signup_enabled: true,
};
const sessionConfig: AuthConfig = {
  ...localConfig,
  auth_mode: "session",
  auto_login: false,
};
const user = {
  id: "user",
  email: "user@example.com",
  is_invited: false,
  is_admin: false,
  scanning_enabled: true,
  pushover_token: null,
};

function appPath(path: string): string {
  return `${import.meta.env.BASE_URL.replace(/\/$/, "")}${path}`;
}

function renderApp(config: AuthConfig = localConfig, path = "/") {
  window.history.replaceState({}, "", appPath(path));
  vi.mocked(fetchAuthConfig).mockResolvedValue(config);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, retryDelay: 0 } },
  });

  return {
    ...render(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>,
    ),
    client,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  auth0.isAuthenticated = false;
  vi.mocked(getMe).mockRejectedValue(
    new AxiosError("Not signed in", "401", undefined, undefined, {
      status: 401,
      data: {},
      statusText: "Unauthorized",
      headers: {},
      config: {} as never,
    }),
  );
  vi.mocked(submitAccessRequest).mockResolvedValue({ message: "Received" });
  vi.mocked(loginSession).mockResolvedValue({ ...user, is_invited: true });
  vi.mocked(logoutSession).mockResolvedValue();
  vi.mocked(listScans).mockResolvedValue({ scans: [], total: 0 });
  vi.mocked(getScan).mockResolvedValue({ id: "test" } as never);
  window.scrollTo = vi.fn();
});

describe("Community pages feature flag", () => {
  const enabled = import.meta.env.VITE_ENABLE_COMMUNITY_PAGES === "true";

  it(`${enabled ? "shows" : "hides"} desktop and mobile navigation`, async () => {
    renderApp();
    await screen.findByRole("link", { name: "Explore" });
    for (const name of ["Ethos", "Contribute"]) {
      expect(screen.queryAllByRole("link", { name })).toHaveLength(
        enabled ? 1 : 0,
      );
    }
    fireEvent.click(screen.getByRole("button", { name: "Toggle mobile menu" }));
    for (const name of ["Ethos", "Contribute"]) {
      const links = screen.queryAllByRole("link", { name });
      expect(links).toHaveLength(enabled ? 2 : 0);
      for (const link of links) {
        expect(link).toHaveAttribute("href", appPath(`/${name.toLowerCase()}`));
      }
    }
  });

  it.each([
    ["/ethos", "Making the Great Outdoors Accessible to All"],
    ["/contribute", "Contribute to camply"],
  ])(
    `${enabled ? "serves" : "redirects"} direct visits to %s`,
    async (path, heading) => {
      renderApp(localConfig, path);
      await screen.findByRole("link", { name: "Explore" });
      if (enabled) {
        expect(
          await screen.findByRole("heading", { name: heading }),
        ).toBeVisible();
        expect(window.location.pathname).toBe(appPath(path));
      } else {
        await waitFor(() =>
          expect(window.location.pathname).toBe(appPath("/")),
        );
        expect(
          screen.queryByRole("heading", { name: heading }),
        ).not.toBeInTheDocument();
      }
    },
  );

  it(`${enabled ? "shows" : "hides"} the Contact contribution card`, async () => {
    renderApp(localConfig, "/contact");
    await screen.findByRole("heading", { name: "Quick Links" });
    expect(screen.queryAllByRole("link", { name: "Contribute" })).toHaveLength(
      enabled ? 2 : 0,
    );
    expect(
      screen.queryAllByRole("heading", { name: "Contribute" }),
    ).toHaveLength(enabled ? 1 : 0);
  });

  it(`${enabled ? "shows" : "hides"} the FAQ contribution link`, async () => {
    renderApp(localConfig, "/faq");
    fireEvent.click(await screen.findByText("How can I contribute to camply?"));
    expect(
      screen.queryAllByRole("link", { name: "Contribute page" }),
    ).toHaveLength(enabled ? 1 : 0);
    expect(
      screen.getAllByRole("link", { name: "GitHub repository" }).length,
    ).toBeGreaterThan(0);
  });

  it(`${enabled ? "shows hosted-service details" : "describes configured app behavior"} on How It Works`, async () => {
    renderApp(localConfig, "/how-it-works");
    expect(
      await screen.findAllByRole("heading", {
        name: enabled ? "We Monitor 24/7" : "Check Availability",
      }),
    ).toHaveLength(enabled ? 1 : 2);

    if (enabled) {
      expect(screen.getByText("Reliable Infrastructure")).toBeVisible();
      expect(screen.getByText("Checks every 2-5 minutes")).toBeVisible();
    } else {
      expect(screen.getByText("What the App Does")).toBeVisible();
      expect(
        screen.getAllByText("Checks on the configured schedule"),
      ).toHaveLength(2);
      expect(
        screen.getAllByText(/review matching availability in your dashboard/i),
      ).toHaveLength(2);
      expect(
        screen.queryByText(/redundancy and failover systems/i),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText(/checks every 2-5 minutes, 24\/7/i),
      ).not.toBeInTheDocument();
    }
  });
});

describe("Application authentication", () => {
  it("opens the notified scan when Auth0 completes while the router is mounted", async () => {
    const { client } = renderApp(auth0Config, "/auth");
    await screen.findByText("Sign in to your camply account");
    const calls = vi.mocked(Auth0Provider).mock.calls;
    const onRedirect = calls[calls.length - 1][0].onRedirectCallback!;
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    act(() => {
      auth0.isAuthenticated = true;
      client.setQueryData(["me"], { ...user, is_invited: true });
      onRedirect({ returnTo: appPath("/dashboard/scans/test#results") });
    });
    expect(
      await screen.findByText("Scan detail", {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(window.location.pathname + window.location.hash).toBe(
      appPath("/dashboard/scans/test#results"),
    );
  });

  it("passes the notification destination through Auth0 login", async () => {
    const destination = "/dashboard/scans/test#results";
    renderApp(auth0Config, destination);
    await screen.findByText("Sign in to your camply account");
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Sign In" })
        .find((button) => button.classList.contains("w-full"))!,
    );
    expect(auth0.loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: appPath(destination) },
      authorizationParams: { screen_hint: "login" },
    });
  });

  it("hides login and signup on desktop and mobile during local auto-login", async () => {
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    renderApp();
    await screen.findByRole("button", { name: "Dashboard" });
    fireEvent.click(screen.getByRole("button", { name: "Toggle mobile menu" }));
    expect(
      screen.queryByRole("button", { name: "Sign In" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sign Up" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get Started" })).toHaveAttribute(
      "href",
      appPath("/dashboard"),
    );
  });

  it("uses the application sign-in page without a Basic credential form", async () => {
    renderApp(auth0Config, "/auth");
    await screen.findByText("Sign in to your camply account");
    const button = screen
      .getAllByRole("button", { name: "Sign In" })
      .find((button) => button.classList.contains("w-full"))!;
    fireEvent.click(button);
    expect(auth0.loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: appPath("/dashboard") },
      authorizationParams: { screen_hint: "login" },
    });
    expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("offers Auth0 signup and passes the API audience to the SDK", async () => {
    renderApp(auth0Config, "/auth?mode=signup");
    const button = await screen.findByRole("button", {
      name: "Create Account",
    });
    fireEvent.click(button);
    expect(auth0.loginWithRedirect).toHaveBeenCalledWith({
      appState: { returnTo: appPath("/dashboard") },
      authorizationParams: { screen_hint: "signup" },
    });
    const calls = vi.mocked(Auth0Provider).mock.calls;
    const props = calls[calls.length - 1][0];
    expect(props).toMatchObject({
      authorizationParams: {
        audience: auth0Config.auth0_audience,
        redirect_uri: new URL(import.meta.env.BASE_URL, window.location.origin)
          .href,
      },
    });
  });

  it("auto-login redirects away from signup and hides login controls", async () => {
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    renderApp({ ...localConfig, auto_login: true }, "/auth?mode=signup");
    await screen.findByText("Scan dashboard");
    expect(window.location.pathname).toBe(appPath("/dashboard"));
    expect(
      screen.queryByRole("button", { name: "Sign In" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sign Up" }),
    ).not.toBeInTheDocument();
  });

  it("local marketing links lead directly to the dashboard", async () => {
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    renderApp({ ...localConfig, auto_login: true });
    expect(
      await screen.findByRole("link", { name: "Get Started" }),
    ).toHaveAttribute("href", appPath("/dashboard"));
  });

  it.each(["/dashboard", "/dashboard/scans/test"])(
    "gates uninvited users at %s",
    async (path) => {
      auth0.isAuthenticated = true;
      vi.mocked(getMe).mockResolvedValue(user);
      renderApp({ ...auth0Config, invite_only: true }, path);
      await screen.findByText("Invitation Required");
      expect(screen.queryByText("Scan dashboard")).not.toBeInTheDocument();
      expect(screen.queryByText("Scan detail")).not.toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Request Access" }));
      await waitFor(() =>
        expect(submitAccessRequest).toHaveBeenCalledWith({
          email: user.email,
          name: null,
        }),
      );
    },
  );

  it("allows uninvited users when invite-only access is off", async () => {
    auth0.isAuthenticated = true;
    vi.mocked(getMe).mockResolvedValue(user);
    renderApp(auth0Config, "/dashboard");
    await screen.findByText("Scan dashboard");
    expect(screen.queryByText("Invitation Required")).not.toBeInTheDocument();
  });

  it("allows invited users when invite-only access is on", async () => {
    auth0.isAuthenticated = true;
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    renderApp({ ...auth0Config, invite_only: true }, "/dashboard");
    await screen.findByText("Scan dashboard");
  });

  it("redirects signed-out protected-route visitors to sign-in", async () => {
    renderApp(auth0Config, "/dashboard");
    await screen.findByText("Sign in to your camply account");
    expect(window.location.pathname).toBe(appPath("/auth"));
  });

  it("does not fall back to Basic login when config loading fails", async () => {
    vi.mocked(fetchAuthConfig).mockRejectedValueOnce(new Error("Offline"));
    renderApp();
    await screen.findByRole("alert");
    expect(
      screen.queryByRole("button", { name: "Sign In" }),
    ).not.toBeInTheDocument();
  });

  it("rejects incomplete Auth0 config instead of showing Basic login", async () => {
    renderApp({ ...auth0Config, auth0_audience: null });
    await screen.findByRole("alert");
    expect(Auth0Provider).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: "Sign In" }),
    ).not.toBeInTheDocument();
  });
});

it("rejects legacy Basic config instead of enabling a credential form", async () => {
  renderApp({ ...localConfig, auth_mode: "basic" as never });
  await screen.findByRole("alert");
  expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
  expect(Auth0Provider).not.toHaveBeenCalled();
});

it("logs in through the password form without showing signup", async () => {
  renderApp(sessionConfig, "/auth?mode=signup");
  fireEvent.change(await screen.findByLabelText("Username"), {
    target: { value: "test-admin" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "synthetic-test-password" },
  });
  expect(
    screen.queryByRole("button", { name: "Sign Up" }),
  ).not.toBeInTheDocument();
  fireEvent.click(
    screen
      .getAllByRole("button", { name: "Sign In" })
      .find((button) => button.getAttribute("type") === "submit")!,
  );
  await screen.findByText("Scan dashboard");
  expect(loginSession).toHaveBeenCalledWith(
    "test-admin",
    "synthetic-test-password",
  );
  expect(Auth0Provider).not.toHaveBeenCalled();
});

it("preserves a cookie session on refresh without retained credentials", async () => {
  vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
  renderApp(sessionConfig, "/dashboard");
  await screen.findByText("Scan dashboard");
  expect(loginSession).not.toHaveBeenCalled();
});

it.each(["/dashboard", "/dashboard/scans/test#results"])(
  "returns to sign-in and clears scan data when the session fails at %s",
  async (path) => {
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    const fetchScan = path === "/dashboard" ? listScans : getScan;
    vi.mocked(fetchScan).mockRejectedValue(
      new AxiosError("Session expired", "401", undefined, undefined, {
        status: 401,
        data: {},
        statusText: "Unauthorized",
        headers: {},
        config: {} as never,
      }),
    );
    const { client } = renderApp(sessionConfig, path);
    client.setQueryData(["scans", "detail", "cached-scan"], {
      id: "cached-scan",
    });

    await screen.findByLabelText("Username");
    expect(window.location.pathname).toBe(appPath("/auth"));
    expect(client.getQueryData(["me"])).toBeNull();
    expect(client.getQueryCache().findAll({ queryKey: ["scans"] })).toEqual([]);
    expect(fetchScan).toHaveBeenCalledTimes(1);
    expect(logoutSession).not.toHaveBeenCalled();

    vi.mocked(listScans).mockResolvedValue({ scans: [], total: 0 });
    vi.mocked(getScan).mockResolvedValue({ id: "test" } as never);
    fireEvent.change(screen.getByLabelText("Username"), {
      target: { value: "test-admin" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "synthetic-test-password" },
    });
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Sign In" })
        .find((button) => button.getAttribute("type") === "submit")!,
    );
    await screen.findByText(
      path === "/dashboard" ? "Scan dashboard" : "Scan detail",
    );
    await waitFor(() =>
      expect(window.location.pathname + window.location.hash).toBe(
        appPath(path),
      ),
    );
    await waitFor(() =>
      expect(
        client.getQueryData(
          path === "/dashboard"
            ? ["scans", "list", undefined]
            : ["scans", "detail", "test"],
        ),
      ).toEqual(
        path === "/dashboard" ? { scans: [], total: 0 } : { id: "test" },
      ),
    );
    expect(
      client.getQueryData(["scans", "detail", "cached-scan"]),
    ).toBeUndefined();
  },
);

it.each([403, 500])(
  "keeps the session after a scan HTTP %s",
  async (status) => {
    vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
    vi.mocked(listScans).mockRejectedValue(
      new AxiosError("Scan failed", "ERR_BAD_REQUEST", undefined, undefined, {
        status,
        data: {},
        statusText: "Scan failed",
        headers: {},
        config: {} as never,
      }),
    );
    const { client } = renderApp(sessionConfig, "/dashboard");

    await screen.findByText("Scan dashboard");
    await waitFor(() =>
      expect(client.getQueryState(["scans", "list", undefined])?.status).toBe(
        "error",
      ),
    );
    expect(client.getQueryData(["me"])).toMatchObject({ id: user.id });
    expect(window.location.pathname).toBe(appPath("/dashboard"));
  },
);

it("routes password-session visitors to sign-in and hides mobile signup", async () => {
  renderApp(sessionConfig, "/dashboard");
  await screen.findByLabelText("Username");
  fireEvent.click(screen.getByRole("button", { name: "Toggle mobile menu" }));
  expect(
    screen.queryByRole("button", { name: "Sign Up" }),
  ).not.toBeInTheDocument();
});

it("clears a password session when signing out from the profile", async () => {
  vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
  renderApp(sessionConfig, "/profile");
  const button = await screen.findByRole("button", { name: "Sign Out" });
  vi.mocked(getMe).mockRejectedValue(
    new AxiosError("Signed out", "401", undefined, undefined, {
      status: 401,
      data: {},
      statusText: "Unauthorized",
      headers: {},
      config: {} as never,
    }),
  );
  fireEvent.click(button);
  await waitFor(() => expect(logoutSession).toHaveBeenCalled());
  await screen.findByRole("button", { name: "Sign In" });
});
