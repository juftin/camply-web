import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { getMe, updateMe, getApiErrorMessage, setAccessTokenProvider } from "@/lib/api";
import type { MeResponse } from "@/lib/structs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AuthMode = "local" | "auth0";

export interface AuthState {
  user: MeResponse | null;
  isLoading: boolean;
  error: string | null;
  isEarlyAccess: boolean;
  isReady: boolean;
  refresh: () => Promise<void>;
  updatePushoverToken: (token: string | null) => Promise<void>;
  signOut: () => void;
  login: () => void;
  authMode: AuthMode;
}

// ---------------------------------------------------------------------------
// Auth mode context (set by App.tsx based on backend /api/auth-config)
// ---------------------------------------------------------------------------

/* eslint-disable-next-line react-refresh/only-export-components */
export const AuthModeContext = createContext<AuthMode>("local");

// ---------------------------------------------------------------------------
// Internal context
// ---------------------------------------------------------------------------

/* eslint-disable-next-line react-refresh/only-export-components */
export const AuthContext = createContext<AuthState | null>(null);

// ---------------------------------------------------------------------------
// Local-mode provider (no Auth0)
// ---------------------------------------------------------------------------

function LocalAuthProvider({ children }: { children: ReactNode }) {
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
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (!isLoading) setInitialLoading(false);
  }, [isLoading]);

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

  const signOut = useCallback(() => {
    queryClient.setQueryData(["me"], null);
    setHasError(null);
  }, [queryClient]);

  const value: AuthState = {
    user: user ?? null,
    isLoading: isLoading || initialLoading,
    error: hasError,
    isEarlyAccess: user?.is_early_access_user ?? false,
    isReady: !initialLoading,
    refresh,
    updatePushoverToken,
    signOut,
    login: () => {},
    authMode: "local" as AuthMode,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Auth0-mode provider
// ---------------------------------------------------------------------------

function Auth0AuthProvider({ children }: { children: ReactNode }) {
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

  const signOut = useCallback(() => {
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
    isEarlyAccess: user?.is_early_access_user ?? false,
    isReady: !initialLoading,
    refresh,
    updatePushoverToken,
    signOut,
    login,
    authMode: "auth0" as AuthMode,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Top-level provider — picks local or auth0 based on AuthModeContext
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const mode = useContext(AuthModeContext);

  if (mode === "auth0") {
    return <Auth0AuthProvider>{children}</Auth0AuthProvider>;
  }
  return <LocalAuthProvider>{children}</LocalAuthProvider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/* eslint-disable-next-line react-refresh/only-export-components */
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
