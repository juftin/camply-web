import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
  type FormEvent,
} from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { AxiosError } from "axios";
import { TentTree } from "lucide-react";
import {
  getMe,
  updateMe,
  getApiErrorMessage,
  setAccessTokenProvider,
  setBasicAuth,
  clearBasicAuth,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { MeResponse } from "@/lib/structs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AuthMode = "basic" | "auth0";

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
export const AuthModeContext = createContext<AuthMode>("basic");

// ---------------------------------------------------------------------------
// Internal context
// ---------------------------------------------------------------------------

/* eslint-disable-next-line react-refresh/only-export-components */
export const AuthContext = createContext<AuthState | null>(null);

// ---------------------------------------------------------------------------
// Basic-auth provider (HTTP Basic Auth — no Auth0)
// ---------------------------------------------------------------------------

function BasicAuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [needsLogin, setNeedsLogin] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginSubmitting, setLoginSubmitting] = useState(false);
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

  // Detect 401 → show login form
  useEffect(() => {
    if (error) {
      const axiosError = error as AxiosError;
      if (axiosError?.response?.status === 401) {
        clearBasicAuth();
        setNeedsLogin(true);
      } else {
        setHasError(getApiErrorMessage(error));
      }
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
    clearBasicAuth();
    queryClient.setQueryData(["me"], null);
    setHasError(null);
    setNeedsLogin(true);
  }, [queryClient]);

  const handleLogin = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setLoginError(null);
      setLoginSubmitting(true);

      const form = e.currentTarget;
      const username = (form.elements.namedItem("username") as HTMLInputElement).value;
      const password = (form.elements.namedItem("password") as HTMLInputElement).value;

      setBasicAuth(username, password);

      try {
        await queryClient.fetchQuery({ queryKey: ["me"], queryFn: getMe });
        setNeedsLogin(false);
      } catch (err) {
        clearBasicAuth();
        const axiosError = err as AxiosError;
        if (axiosError?.response?.status === 401) {
          setLoginError("Invalid username or password.");
        } else {
          setLoginError(getApiErrorMessage(err));
        }
      } finally {
        setLoginSubmitting(false);
      }
    },
    [queryClient],
  );

  // Show login form when credentials needed
  if (needsLogin) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4">
        <div className="text-center mb-6">
          <TentTree className="h-10 w-10 text-primary mx-auto" />
          <h1 className="text-2xl font-bold mt-2">camply</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Sign in to manage your campsite scans
          </p>
        </div>

        <Card className="w-full max-w-sm">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-lg">Sign In</CardTitle>
            <CardDescription>
              Enter your camply credentials
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  autoFocus
                  required
                  disabled={loginSubmitting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  disabled={loginSubmitting}
                />
              </div>
              {loginError && (
                <p className="text-sm text-destructive">{loginError}</p>
              )}
              <Button type="submit" className="w-full" disabled={loginSubmitting}>
                {loginSubmitting ? "Signing in…" : "Sign In"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Loading state while fetching user
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const value: AuthState = {
    user: user ?? null,
    isLoading: false,
    error: hasError,
    isEarlyAccess: user?.is_early_access_user ?? false,
    isReady: true,
    refresh,
    updatePushoverToken,
    signOut,
    login: () => {},
    authMode: "basic" as AuthMode,
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
// Top-level provider — picks basic or auth0 based on AuthModeContext
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const mode = useContext(AuthModeContext);

  if (mode === "auth0") {
    return <Auth0AuthProvider>{children}</Auth0AuthProvider>;
  }
  return <BasicAuthProvider>{children}</BasicAuthProvider>;
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
