// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

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
import { getMe, updateMe, getApiErrorMessage, setAuth0TokenProvider } from "@/lib/api";
import type { MeResponse } from "@/lib/structs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthState {
  /** The current user profile, or ``null`` while loading. */
  user: MeResponse | null;
  /** ``true`` while the initial auth check request is in flight. */
  isLoading: boolean;
  /** Non-null if the auth check failed. */
  error: string | null;
  /** Shorthand: is the user an early-access whitelisted user? */
  isEarlyAccess: boolean;
  /** True when we've finished the initial load (user resolved or error). */
  isReady: boolean;
  /** Refresh the user profile from the server. */
  refresh: () => Promise<void>;
  /** Update the user's pushover token. */
  updatePushoverToken: (token: string | null) => Promise<void>;
  /** Sign out (clear local state). */
  signOut: () => void;
  /** Whether Auth0 mode is active. */
  isAuth0Mode: boolean;
  /** Sign in via Auth0 redirect. */
  loginWithAuth0: () => void;
  /** Whether an Auth0 action (login/redirect) is in progress. */
  auth0IsLoading: boolean;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthState | null>(null);

// ---------------------------------------------------------------------------
// Provider component
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [initialLoading, setInitialLoading] = useState(true);
  const [hasError, setHasError] = useState<string | null>(null);

  // Auth0 hooks — safe to call even when Auth0Provider isn't wrapping
  // (useAuth0 returns { isAuthenticated: false, isLoading: false } gracefully)
  const auth0 = useAuth0();
  const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
  const isAuth0Mode = Boolean(auth0Domain);

  // Connect the Auth0 token provider to the Axios interceptor
  useEffect(() => {
    if (isAuth0Mode && auth0.isAuthenticated && auth0.getAccessTokenSilently) {
      setAuth0TokenProvider(async () => {
        try {
          const token = await auth0.getAccessTokenSilently();
          return token;
        } catch {
          return null;
        }
      });
    }
  }, [isAuth0Mode, auth0.isAuthenticated, auth0.getAccessTokenSilently]);

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
    // In Auth0 mode, only run the query once auth0 has resolved
    enabled: !isAuth0Mode || (!auth0.isLoading && auth0.isAuthenticated),
  });

  // Track initial loading state
  useEffect(() => {
    if (!isLoading) {
      // In Auth0 mode wait for auth0 too
      if (!isAuth0Mode || !auth0.isLoading) {
        setInitialLoading(false);
      }
    }
  }, [isLoading, isAuth0Mode, auth0.isLoading]);

  useEffect(() => {
    if (error) {
      setHasError(getApiErrorMessage(error));
    } else {
      setHasError(null);
    }
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
    // In Auth0 mode, also log out of Auth0
    if (isAuth0Mode) {
      void auth0.logout({
        logoutParams: { returnTo: window.location.origin },
      });
    }
  }, [queryClient, isAuth0Mode, auth0]);

  const loginWithAuth0 = useCallback(() => {
    void auth0.loginWithRedirect();
  }, [auth0]);

  const value: AuthState = {
    user: user ?? null,
    isLoading: isLoading || initialLoading || auth0.isLoading,
    error: hasError,
    isEarlyAccess: user?.is_early_access_user ?? false,
    isReady: !initialLoading,
    refresh,
    updatePushoverToken,
    signOut,
    isAuth0Mode,
    loginWithAuth0,
    auth0IsLoading: auth0.isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
