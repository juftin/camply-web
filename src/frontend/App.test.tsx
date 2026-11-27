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
import { App as NativeApp, type URLOpenListenerEvent } from "@capacitor/app";
import { Browser } from "@capacitor/browser";
import { Capacitor } from "@capacitor/core";
import { AxiosError } from "axios";
import App from "./App";
import {
  fetchAuthConfig,
  getMe,
  submitAccessRequest,
  loginSession,
  logoutSession,
  listMySessions,
  revokeMySession,
  listScans,
  getScan,
} from "@/lib/api";
import type { AuthConfig } from "@/lib/api";
import { useScans, useScanDetail } from "@/hooks/useScans";
import { loadMobileServer, saveMobileServer } from "@/lib/mobile-server";

const auth0 = vi.hoisted(() => ({
  isAuthenticated: false,
  isLoading: false,
  user: undefined as { sub?: string } | undefined,
  error: undefined as Error | undefined,
  getAccessTokenSilently: vi.fn().mockResolvedValue("token"),
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
  handleRedirectCallback: vi.fn(),
}));

vi.mock("@capacitor/app", () => ({
  App: { addListener: vi.fn(), getLaunchUrl: vi.fn() },
}));
vi.mock("@capacitor/browser", () => ({
  Browser: { open: vi.fn(), close: vi.fn() },
}));
vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: vi.fn(() => false) },
}));
vi.mock("@capacitor/preferences", () => ({
  Preferences: {
    get: async ({ key }: { key: string }) => ({
      value: localStorage.getItem(`test-preference:${key}`),
    }),
    set: async ({ key, value }: { key: string; value: string }) =>
      localStorage.setItem(`test-preference:${key}`, value),
  },
}));

vi.mock("@auth0/auth0-react", () => ({
  Auth0Provider: vi.fn(({ children }: { children: ReactNode }) => children),
  useAuth0: () => auth0,
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchAuthConfig: vi.fn(),
    getMe: vi.fn(),
    updateMe: vi.fn(),
    sendTestNotification: vi.fn(),
    loginSession: vi.fn(),
    logoutSession: vi.fn(),
    listMySessions: vi.fn().mockResolvedValue({ items: [] }),
    revokeMySession: vi.fn().mockResolvedValue(undefined),
    listScans: vi.fn(),
    getScan: vi.fn(),
    submitAccessRequest: vi.fn(),
    setAccessTokenProvider: vi.fn(),
  };
});

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

beforeEach(async () => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
  await loadMobileServer();
  vi.mocked(NativeApp.addListener).mockResolvedValue({
    remove: vi.fn().mockResolvedValue(undefined),
  });
  vi.mocked(NativeApp.getLaunchUrl).mockResolvedValue(undefined);
  vi.mocked(Browser.open).mockResolvedValue(undefined);
  auth0.isAuthenticated = false;
  auth0.isLoading = false;
  auth0.user = undefined;
  auth0.error = undefined;
  auth0.getAccessTokenSilently.mockResolvedValue("token");
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
  it("uses the native Auth0 client and accepts only its app callback", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await loadMobileServer();
    vi.stubEnv("VITE_MOBILE_AUTH0_CLIENT_ID", "native-client");
    const redirectUri = "com.camply.mobile://auth/callback";
    const nativeCallback = `${redirectUri}?code=synthetic-code&state=synthetic-state`;
    const remove = vi.fn().mockResolvedValue(undefined);
    vi.mocked(NativeApp.addListener).mockResolvedValue({ remove });
    vi.mocked(NativeApp.getLaunchUrl).mockResolvedValue({
      url: nativeCallback,
    });
    auth0.handleRedirectCallback.mockResolvedValue({});
    vi.mocked(Browser.open).mockResolvedValue(undefined);
    vi.mocked(Browser.close).mockResolvedValue(undefined);

    try {
      const { unmount } = renderApp(auth0Config, "/auth");
      await screen.findByText("Sign in to your camply account");
      expect(Auth0Provider).toHaveBeenLastCalledWith(
        expect.objectContaining({
          clientId: "native-client",
          cacheLocation: "memory",
          useRefreshTokensFallback: false,
          authorizationParams: expect.objectContaining({
            redirect_uri: redirectUri,
          }),
        }),
        expect.anything(),
      );
      fireEvent.click(
        screen
          .getAllByRole("button", { name: "Sign In" })
          .find((button) => button.classList.contains("w-full"))!,
      );
      const options = auth0.loginWithRedirect.mock.lastCall?.[0];
      const authorizeUrl = "https://test.example.com/authorize";
      await options.openUrl(authorizeUrl);
      expect(Browser.open).toHaveBeenCalledWith({ url: authorizeUrl });

      await waitFor(() =>
        expect(auth0.handleRedirectCallback).toHaveBeenCalledWith(
          nativeCallback,
        ),
      );
      expect(NativeApp.addListener).toHaveBeenCalledWith(
        "appUrlOpen",
        expect.any(Function),
      );
      const onAppUrlOpen = vi.mocked(NativeApp.addListener).mock
        .lastCall![1] as unknown as (event: URLOpenListenerEvent) => void;
      await act(async () => {
        onAppUrlOpen({ url: nativeCallback });
        onAppUrlOpen({ url: nativeCallback.replace("//auth/", "//other/") });
      });
      expect(auth0.handleRedirectCallback).toHaveBeenCalledTimes(1);
      expect(Browser.close).toHaveBeenCalledTimes(1);
      unmount();
      await waitFor(() => expect(remove).toHaveBeenCalledOnce());
    } finally {
      vi.unstubAllEnvs();
      vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    }
  });

  it("explains cookie-session availability in native builds", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await saveMobileServer("https://camply.example/camply", "");
    await loadMobileServer();
    try {
      renderApp(sessionConfig);
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Open Camply in your browser to use this deployment’s password sign-in.",
      );
      expect(
        screen.getByRole("link", { name: "Open Camply in browser" }),
      ).toHaveAttribute("href", "https://camply.example/camply/");
      expect(Auth0Provider).not.toHaveBeenCalled();
    } finally {
      vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    }
  });

  it("signs in natively when the server advertises password-session support", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await loadMobileServer();
    renderApp({ ...sessionConfig, native_password_sessions: true }, "/auth");
    fireEvent.change(await screen.findByLabelText("Username"), {
      target: { value: "test-user" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "synthetic-password" },
    });
    fireEvent.click(
      screen
        .getAllByRole("button", { name: "Sign In" })
        .find((button) => button.getAttribute("type") === "submit")!,
    );
    await waitFor(() =>
      expect(loginSession).toHaveBeenCalledWith(
        "test-user",
        "synthetic-password",
      ),
    );
    expect(await screen.findByText("Scan dashboard")).toBeInTheDocument();
  });

  it.each([false, true])(
    "allows retry when the Auth0 browser fails to open (signup=%s)",
    async (signup) => {
      vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
      await saveMobileServer("https://camply.example", "native-client");
      await loadMobileServer();
      const authorizeUrl = "https://test.example.com/authorize";
      auth0.loginWithRedirect.mockImplementationOnce(
        async ({ openUrl }) => await openUrl(authorizeUrl),
      );
      vi.mocked(Browser.open).mockRejectedValueOnce(
        new Error("Unable to display URL"),
      );
      renderApp(auth0Config, signup ? "/auth?mode=signup" : "/auth");
      const name = signup ? "Create Account" : "Sign In";
      await screen.findByText(
        signup
          ? "Sign up to start monitoring campsite availability"
          : "Sign in to your camply account",
      );
      const button = screen
        .getAllByRole("button", { name })
        .find((candidate) => candidate.classList.contains("w-full"))!;
      fireEvent.click(button);
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Could not open the sign-in page",
      );
      expect(button).toBeEnabled();
      auth0.loginWithRedirect.mockImplementationOnce(
        async ({ openUrl }) => await openUrl(authorizeUrl),
      );
      fireEvent.click(button);
      await waitFor(() => expect(Browser.open).toHaveBeenCalledTimes(2));
      expect(screen.queryByRole("alert")).toBeNull();
    },
  );

  it("waits for the logout browser and lets the user retry after local sign-out", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await saveMobileServer("https://camply.example", "native-client");
    await loadMobileServer();
    auth0.isAuthenticated = true;
    auth0.user = { sub: "test-user" };
    vi.mocked(getMe).mockResolvedValue(user);
    const logoutUrl = "https://test.example.com/v2/logout";
    auth0.logout.mockImplementationOnce(
      async ({ openUrl }) => await openUrl(logoutUrl),
    );
    let rejectBrowser!: (error: Error) => void;
    vi.mocked(Browser.open).mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          rejectBrowser = reject;
        }),
    );
    const { client } = renderApp(auth0Config, "/profile");
    fireEvent.click(await screen.findByRole("button", { name: "Sign Out" }));
    await waitFor(() =>
      expect(Browser.open).toHaveBeenCalledWith({ url: logoutUrl }),
    );
    expect(window.location.pathname).toBe(appPath("/profile"));
    await act(async () => rejectBrowser(new Error("Unable to display URL")));
    expect(
      await screen.findByText(
        /Could not open the browser to finish signing out/,
      ),
    ).toBeVisible();
    expect(client.getQueryData(["me"])).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(Browser.open).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(
        screen.queryByText(/Could not open the browser to finish signing out/),
      ).toBeNull(),
    );
  });

  it("retries the selected deployment after a connection failure", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await saveMobileServer("https://camply.example", "");
    await loadMobileServer();
    vi.mocked(fetchAuthConfig).mockRejectedValueOnce(new Error("Offline"));

    renderApp({ ...sessionConfig, native_password_sessions: true }, "/auth");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not connect to camply.example",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Username")).toBeVisible();
    expect(fetchAuthConfig).toHaveBeenCalledTimes(2);
  });

  it("allows server recovery when the selected deployment is unavailable", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    await saveMobileServer("https://unavailable.example/camply", "old-client");
    await loadMobileServer();
    const replace = vi.fn();
    vi.stubGlobal("location", { replace });
    sessionStorage.setItem("previous-auth-transaction", "synthetic-state");
    try {
      vi.mocked(fetchAuthConfig).mockRejectedValueOnce(new Error("Offline"));
      render(
        <QueryClientProvider client={new QueryClient()}>
          <App />
        </QueryClientProvider>,
      );
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "unavailable.example",
      );
      fireEvent.click(screen.getByRole("button", { name: "Server settings" }));
      const serverUrl = screen.getByLabelText("Server URL");
      expect(serverUrl).toHaveValue("https://unavailable.example/camply/");
      fireEvent.change(serverUrl, {
        target: { value: "http://camply.example" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Connect" }));
      expect(
        await screen.findByText(/Enter an HTTPS server URL/),
      ).toBeVisible();
      fireEvent.click(screen.getByRole("button", { name: "Use camply.rocks" }));
      expect(serverUrl).toHaveValue("https://camply.rocks/");
      fireEvent.click(screen.getByRole("button", { name: "Connect" }));
      await waitFor(() =>
        expect(replace).toHaveBeenCalledWith(import.meta.env.BASE_URL),
      );
      expect(await loadMobileServer()).toEqual({
        url: "https://camply.rocks/",
        auth0ClientId: "",
      });
      expect(sessionStorage.getItem("previous-auth-transaction")).toBeNull();
      expect(replace).toHaveBeenCalledWith(import.meta.env.BASE_URL);
    } finally {
      vi.unstubAllGlobals();
      vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    }
  });

  it("does not reuse the hosted Auth0 client ID on a different server", async () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    vi.stubEnv("VITE_MOBILE_AUTH0_CLIENT_ID", "hosted-client");
    await saveMobileServer("https://camply.example/trips", "");
    await loadMobileServer();
    try {
      renderApp(auth0Config, "/auth");
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "native Auth0 client ID",
      );
      expect(Auth0Provider).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllEnvs();
      vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    }
  });

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
      await screen.findByText("Scan detail", {}, { timeout: 10000 }),
    ).toBeInTheDocument();
    expect(window.location.pathname + window.location.hash).toBe(
      appPath("/dashboard/scans/test#results"),
    );
  }, 15000);

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
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
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
      cacheLocation: "memory",
      useRefreshTokens: true,
      useRefreshTokensFallback: true,
      authorizationParams: {
        audience: auth0Config.auth0_audience,
        redirect_uri: new URL(import.meta.env.BASE_URL, window.location.origin)
          .href,
      },
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("surfaces Auth0 SDK errors cleanly without redirecting in a loop", async () => {
    auth0.error = Object.assign(new Error("Missing refresh token"), {
      error: "missing_refresh_token",
    });
    renderApp(auth0Config, "/dashboard");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      /session has expired\. please sign in again/i,
    );
    expect(window.location.pathname).toBe(appPath("/dashboard"));
    expect(screen.getByRole("link", { name: "Sign In" })).toHaveAttribute(
      "href",
      expect.stringContaining("/auth?returnTo="),
    );
    expect(auth0.loginWithRedirect).not.toHaveBeenCalled();
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

it("transitions cleanly to /auth when revoking the current session from the profile", async () => {
  vi.mocked(getMe).mockResolvedValue({ ...user, is_invited: true });
  vi.mocked(listMySessions).mockResolvedValue({
    items: [
      {
        id: "sess-current",
        user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/130.0.0.0",
        ip_address: "198.51.100.1",
        created_at: "2026-11-15T10:00:00Z",
        expires_at: "2026-11-22T10:00:00Z",
        is_current: true,
      },
    ],
  });
  vi.mocked(revokeMySession).mockResolvedValue(undefined);

  renderApp(sessionConfig, "/profile");

  const revokeButton = await screen.findByRole("button", { name: "Revoke" });
  vi.mocked(getMe).mockRejectedValue(
    new AxiosError("Session revoked", "401", undefined, undefined, {
      status: 401,
      data: {},
      statusText: "Unauthorized",
      headers: {},
      config: {} as never,
    }),
  );
  fireEvent.click(revokeButton);

  await waitFor(() =>
    expect(revokeMySession).toHaveBeenCalledWith("sess-current"),
  );
  await screen.findByLabelText("Username");
  expect(logoutSession).not.toHaveBeenCalled();
  await waitFor(() => expect(window.location.pathname).toBe(appPath("/auth")));
});
