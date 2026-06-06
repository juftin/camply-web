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
import { getMe, updateMe, getApiErrorMessage } from "@/lib/api";
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

  // Track initial loading state
  useEffect(() => {
    if (!isLoading) {
      setInitialLoading(false);
    }
  }, [isLoading]);

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
