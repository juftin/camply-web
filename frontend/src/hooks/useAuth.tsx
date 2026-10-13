import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { useAuth0 } from "@auth0/auth0-react";
import {
  getMe,
  logoutSession,
  updateMe,
  getApiErrorMessage,
  setAccessTokenProvider,
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
  signOut: () => void;
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
      predicate: (query) => query.queryKey[0] !== "me",
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
    getAccessTokenSilently,
    loginWithRedirect,
    logout,
  } = useAuth0();

  const queryClient = useQueryClient();
  const [initialLoading, setInitialLoading] = useState(true);
  const [hasError, setHasError] = useState<string | null>(null);

  // Register the token provider so axios can attach Bearer tokens.
  useEffect(() => {
    setAccessTokenProvider(async () => {
      if (!isAuthenticated) return null;
      try {
        return await getAccessTokenSilently();
      } catch {
        return null;
      }
    });
  }, [isAuthenticated, getAccessTokenSilently]);

  const {
    data: user,
    error,
    isLoading: meLoading,
    refetch,
  } = useQuery<MeResponse>({
    queryKey: ["me"],
    queryFn: getMe,
    retry: 1,
    staleTime: 5 * 60 * 1000,
    enabled: isAuthenticated && !auth0Loading,
  });

  useEffect(() => {
    if (!auth0Loading && (!isAuthenticated || !meLoading)) {
      setInitialLoading(false);
    }
  }, [auth0Loading, isAuthenticated, meLoading]);

  useEffect(() => {
    if (error) setHasError(getApiErrorMessage(error));
    else setHasError(null);
  }, [error]);

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
    await queryClient.cancelQueries();
    queryClient.removeQueries({
      predicate: (query) => query.queryKey[0] !== "me",
    });
    queryClient.setQueryData(["me"], null);
    setHasError(null);
    logout({ logoutParams: { returnTo: window.location.origin } });
  }, [queryClient, logout]);

  const login = useCallback(() => {
    loginWithRedirect();
  }, [loginWithRedirect]);

  const value: AuthState = {
    user: user ?? null,
    isLoading: initialLoading,
    error: hasError,
    isInvited: user?.is_invited ?? false,
    isAdmin: user?.is_admin ?? false,
    isScanningEnabled: user?.scanning_enabled ?? true,
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
      user || config.auto_login
        ? "/dashboard"
        : config.signup_enabled
          ? "/auth?mode=signup"
          : "/auth",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Top-level provider — owner-selected shared-account login or Auth0
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const config = useContext(AuthConfigContext);

  if (config.auth_mode === "auth0") {
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
