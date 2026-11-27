import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import { auth0BrowserOptions, mobileAuthCallback } from "@/lib/mobile-auth";
import {
  getMe,
  logoutSession,
  updateMe,
  getApiErrorMessage,
  setAccessTokenProvider,
  setApiAuthMode,
  classifyTokenAcquisitionError,
  shouldRetryProtectedQuery,
  type AuthConfig,
} from "@/lib/api";
import type { MeResponse } from "@/lib/structs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AuthMode = AuthConfig["auth_mode"];

export interface AuthState {
  user: MeResponse | null;
  isLoading: boolean;
  error: string | null;
  isInvited: boolean;
  isAdmin: boolean;
  isScanningEnabled: boolean;
  isReady: boolean;
  refresh: () => Promise<void>;
  updatePushoverToken: (token: string | null) => Promise<void>;
  signOut: () => Promise<void>;
  login: () => void;
  authMode: AuthMode;
  inviteOnly: boolean;
  autoLogin: boolean;
  signupEnabled: boolean;
  accountPath: string;
}

// ---------------------------------------------------------------------------
// Auth mode context (set by App.tsx based on backend /api/auth-config)
// ---------------------------------------------------------------------------

/* oxlint-disable-next-line react/only-export-components */
export const AuthConfigContext = createContext<AuthConfig>({
  auth_mode: "none",
  auth0_domain: null,
  auth0_client_id: null,
  auth0_audience: null,
  invite_only: false,
  auto_login: true,
  signup_enabled: false,
});

// ---------------------------------------------------------------------------
// Internal context
// ---------------------------------------------------------------------------

/* oxlint-disable-next-line react/only-export-components */
export const AuthContext = createContext<AuthState | null>(null);

// ---------------------------------------------------------------------------
// Automatic shared-account login or in-app password sessions
// ---------------------------------------------------------------------------

function CookieAuthProvider({ children }: { children: ReactNode }) {
  const config = useContext(AuthConfigContext);
  const queryClient = useQueryClient();
  const [initialLoading, setInitialLoading] = useState(true);
  const [hasError, setHasError] = useState<string | null>(null);

  const {
    data: user,
    error,
    isLoading,
    refetch,
  } = useQuery<MeResponse>({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const signedOut =
    !config.auto_login &&
    error instanceof AxiosError &&
    error.response?.status === 401;

  useEffect(() => {
    setApiAuthMode(config.auth_mode);
  }, [config.auth_mode]);

  useEffect(() => {
    if (!isLoading) setInitialLoading(false);
  }, [isLoading]);

  useEffect(() => {
    setHasError(error && !signedOut ? getApiErrorMessage(error) : null);
  }, [error, signedOut]);

  useEffect(() => {
    if (config.auth_mode !== "session") return;
    return queryClient.getQueryCache().subscribe((event) => {
      if (
        event.type === "updated" &&
        event.action.type === "error" &&
        event.query.queryKey[0] === "scans" &&
        event.query.state.error instanceof AxiosError &&
        event.query.state.error.response?.status === 401
      ) {
        void queryClient.cancelQueries({ queryKey: ["me"] });
        queryClient.setQueryData(["me"], null);
        queryClient.removeQueries({ queryKey: ["scans"] });
        setHasError(null);
      }
    });
  }, [config.auth_mode, queryClient]);

  const pushoverMutation = useMutation({
    mutationFn: (token: string | null) => updateMe({ pushover_token: token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const updatePushoverToken = useCallback(
    async (token: string | null) => {
      await pushoverMutation.mutateAsync(token);
      await refetch();
    },
    [pushoverMutation, refetch],
  );

  const refresh = useCallback(async () => {
    setHasError(null);
    await refetch();
  }, [refetch]);

  const signOut = useCallback(async () => {
    if (config.auto_login) return;
    try {
      await logoutSession();
    } catch (error) {
      if (!(error instanceof AxiosError && error.response?.status === 401)) {
        setHasError(getApiErrorMessage(error));
        return;
      }
    }
    await queryClient.cancelQueries();
    queryClient.removeQueries({
      predicate: (query) =>
        !(query.queryKey.length === 1 && query.queryKey[0] === "me"),
    });
    queryClient.setQueryData(["me"], null);
    setHasError(null);
  }, [config.auto_login, queryClient]);
  const login = useCallback(() => {}, []);

  const currentUser = signedOut ? null : user;
  const value: AuthState = {
    user: currentUser ?? null,
    isLoading: isLoading || initialLoading,
    error: hasError,
    isInvited: currentUser?.is_invited ?? false,
    isAdmin: currentUser?.is_admin ?? false,
    isScanningEnabled: currentUser?.scanning_enabled ?? true,
    isReady: !initialLoading,
    refresh,
    updatePushoverToken,
    signOut,
    login,
    authMode: config.auth_mode,
    inviteOnly: config.invite_only,
    autoLogin: config.auto_login,
    signupEnabled: config.signup_enabled,
    accountPath:
      currentUser || config.auto_login
        ? "/dashboard"
        : config.signup_enabled
          ? "/auth?mode=signup"
          : "/auth",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Auth0-mode provider
// ---------------------------------------------------------------------------

function Auth0AuthProvider({ children }: { children: ReactNode }) {
  const config = useContext(AuthConfigContext);
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    error: auth0Error,
    getAccessTokenSilently,
    loginWithRedirect,
    logout,
  } = useAuth0();

  const queryClient = useQueryClient();
  const [initialLoading, setInitialLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [logoutBrowserUrl, setLogoutBrowserUrl] = useState<string | null>(null);
  const lastSubRef = useRef<string | undefined>(auth0User?.sub);
  const wasAuthenticatedRef = useRef<boolean>(isAuthenticated);

  const clearProtectedCaches = useCallback(
    (clearMe: "null" | "remove" = "null", removeImmediately = false) => {
      void queryClient.cancelQueries();
      if (clearMe === "remove") {
        queryClient.removeQueries({ queryKey: ["me"] });
      } else {
        queryClient.setQueryData(["me"], null);
      }
      if (removeImmediately) {
        queryClient.removeQueries({ queryKey: ["scans"] });
        queryClient.removeQueries({ queryKey: ["admin"] });
      }
    },
    [queryClient],
  );

  // Register the token provider and auth error handlers so axios can attach and renew Bearer tokens.
  useEffect(() => {
    setApiAuthMode("auth0");
    setAccessTokenProvider(
      async (options) => {
        if (!isAuthenticated) return null;
        try {
          return (await getAccessTokenSilently(options)) ?? null;
        } catch (err) {
          throw classifyTokenAcquisitionError(err);
        }
      },
      {
        onSessionExpired: (expiredError) => {
          clearProtectedCaches("null");
          setSessionError(expiredError.message);
        },
        onAuthFailure: (authFailure) => {
          clearProtectedCaches("null");
          setSessionError(authFailure.message);
        },
      },
    );
    return () => {
      setAccessTokenProvider(null);
      setApiAuthMode("none");
    };
  }, [isAuthenticated, getAccessTokenSilently, clearProtectedCaches]);

  // Clear cached user and protected data on account switch or session termination.
  useEffect(() => {
    const currentSub = auth0User?.sub;
    const prevSub = lastSubRef.current;

    if (prevSub && currentSub && prevSub !== currentSub) {
      clearProtectedCaches("remove", true);
      setSessionError(null);
      setSignedOut(false);
      setLogoutBrowserUrl(null);
      lastSubRef.current = currentSub;
      wasAuthenticatedRef.current = isAuthenticated;
      return;
    }

    if (wasAuthenticatedRef.current && !isAuthenticated && !auth0Loading) {
      clearProtectedCaches("null");
      lastSubRef.current = undefined;
    } else if (!wasAuthenticatedRef.current && isAuthenticated) {
      setSessionError(null);
      setSignedOut(false);
      setLogoutBrowserUrl(null);
      if (queryClient.getQueryData(["me"]) === null) {
        queryClient.removeQueries({ queryKey: ["me"] });
      }
    }

    if (currentSub) {
      lastSubRef.current = currentSub;
    }
    wasAuthenticatedRef.current = isAuthenticated;
  }, [
    auth0User?.sub,
    isAuthenticated,
    auth0Loading,
    clearProtectedCaches,
    queryClient,
  ]);

  const {
    data: user,
    error,
    isLoading: meLoading,
    refetch,
  } = useQuery<MeResponse | null>({
    queryKey: ["me"],
    queryFn: getMe,
    retry: shouldRetryProtectedQuery,
    staleTime: 5 * 60 * 1000,
    enabled: isAuthenticated && !auth0Loading && !sessionError && !signedOut,
  });

  // Remove protected caches after React commits user=null so disabled observers do not re-fetch.
  useEffect(() => {
    if (
      !user &&
      (sessionError || signedOut || (!isAuthenticated && !auth0Loading))
    ) {
      queryClient.removeQueries({ queryKey: ["scans"] });
      queryClient.removeQueries({ queryKey: ["admin"] });
    }
  }, [
    user,
    sessionError,
    signedOut,
    isAuthenticated,
    auth0Loading,
    queryClient,
  ]);

  useEffect(() => {
    if (
      !auth0Loading &&
      (!isAuthenticated || !meLoading || Boolean(sessionError))
    ) {
      setInitialLoading(false);
    }
  }, [auth0Loading, isAuthenticated, meLoading, sessionError]);

  const pushoverMutation = useMutation({
    mutationFn: (token: string | null) => updateMe({ pushover_token: token }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const updatePushoverToken = useCallback(
    async (token: string | null) => {
      await pushoverMutation.mutateAsync(token);
      await refetch();
    },
    [pushoverMutation, refetch],
  );

  const refresh = useCallback(async () => {
    setSessionError(null);
    setSignedOut(false);
    await refetch();
  }, [refetch]);

  const openLogoutBrowser = useCallback(async (url: string) => {
    const { openUrl } = auth0BrowserOptions();
    try {
      await openUrl?.(url);
      setLogoutBrowserUrl(null);
    } catch {
      // Complete the SDK's local logout and retain the browser URL for a retry.
      setLogoutBrowserUrl(url);
    }
  }, []);

  const signOut = useCallback(async () => {
    const native = Boolean(auth0BrowserOptions().openUrl);
    await logout({
      ...(native && { openUrl: openLogoutBrowser }),
      logoutParams: {
        returnTo: native ? mobileAuthCallback : window.location.origin,
      },
    });
    lastSubRef.current = undefined;
    setSessionError(null);
    setSignedOut(true);
    await queryClient.cancelQueries();
    queryClient.setQueryData(["me"], null);
    queryClient.removeQueries({ queryKey: ["scans"] });
    queryClient.removeQueries({ queryKey: ["admin"] });
  }, [queryClient, logout, openLogoutBrowser]);

  const login = useCallback(() => {
    setSessionError(null);
    setSignedOut(false);
    loginWithRedirect(auth0BrowserOptions());
  }, [loginWithRedirect]);

  const effectiveLoading =
    initialLoading ||
    auth0Loading ||
    (isAuthenticated && !sessionError && !signedOut && meLoading);
  const auth0ClassifiedError = auth0Error
    ? classifyTokenAcquisitionError(auth0Error).message
    : null;
  const resolvedError =
    sessionError ??
    auth0ClassifiedError ??
    (error ? getApiErrorMessage(error) : null);

  const value: AuthState = {
    user: user ?? null,
    isLoading: effectiveLoading,
    error: resolvedError,
    isInvited: user?.is_invited ?? false,
    isAdmin: user?.is_admin ?? false,
    isScanningEnabled: user?.scanning_enabled ?? true,
    isReady: !effectiveLoading,
    refresh,
    updatePushoverToken,
    signOut,
    login,
    authMode: config.auth_mode,
    inviteOnly: config.invite_only,
    autoLogin: config.auto_login,
    signupEnabled: config.signup_enabled,
    accountPath:
      user || config.auto_login
        ? "/dashboard"
        : config.signup_enabled
          ? "/auth?mode=signup"
          : "/auth",
  };

  return (
    <AuthContext.Provider value={value}>
      {signedOut && logoutBrowserUrl && (
        <div role="alert" className="space-y-2 border-b p-4 text-center">
          <p>
            Signed out of Camply. Could not open the browser to finish signing
            out of Auth0.
          </p>
          <Button
            variant="outline"
            onClick={() => void openLogoutBrowser(logoutBrowserUrl)}
          >
            Try again
          </Button>
        </div>
      )}
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Top-level provider — owner-selected shared-account login or Auth0
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const config = useContext(AuthConfigContext);

  if (!config.auto_login && config.auth_mode === "auth0") {
    return <Auth0AuthProvider>{children}</Auth0AuthProvider>;
  }
  return <CookieAuthProvider>{children}</CookieAuthProvider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/* oxlint-disable-next-line react/only-export-components */
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
