import * as React from "react";
import { TentTree } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";
import { AxiosError } from "axios";
import { useQueryClient } from "@tanstack/react-query";
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
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/useAuth";
import { getMe, setBasicAuth, clearBasicAuth, getApiErrorMessage } from "@/lib/api";

function Auth0Content() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithRedirect } = useAuth0();
  const { isReady, user } = useAuth();
  const isSignUp = searchParams.get("mode") === "signup";

  // Redirect authenticated users to dashboard.
  React.useEffect(() => {
    if (isReady && user) {
      navigate("/dashboard", { replace: true });
    }
  }, [isReady, user, navigate]);

  const handleLogin = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: "login",
      },
    });
  };

  const handleSignUp = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: "signup",
      },
    });
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center px-4 py-6">
        <div className="w-full max-w-md">
          <div className="text-center mb-6">
            <Link to="/" className="inline-flex items-center space-x-2">
              <TentTree className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold">camply</span>
            </Link>
            <p className="text-muted-foreground mt-1 text-sm">
              Never miss your perfect campsite
            </p>
          </div>

          <Card>
            <CardHeader className="text-center pb-4">
              <CardTitle className="text-xl">
                {isSignUp ? "Create Account" : "Let's Go Camping"}
              </CardTitle>
              <CardDescription className="text-sm">
                {isSignUp
                  ? "Sign up to start monitoring campsite availability"
                  : "Sign in to your camply account"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                className="w-full"
                onClick={isSignUp ? handleSignUp : handleLogin}
              >
                {isSignUp ? "Create Account" : "Sign In"}
              </Button>

              <div className="mt-6 text-center">
                <span className="text-muted-foreground">
                  {isSignUp
                    ? "Already have an account?"
                    : "Don't have an account?"}
                </span>{" "}
                <Link
                  to={isSignUp ? "/auth" : "/auth?mode=signup"}
                  className="text-primary hover:text-primary/80 font-medium"
                >
                  {isSignUp ? "Sign in" : "Sign up"}
                </Link>
              </div>
            </CardContent>
          </Card>

          <div className="mt-4 text-center text-xs text-muted-foreground">
            By continuing, you agree to our{" "}
            <Link to="/terms" className="text-primary hover:text-primary/80">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link to="/privacy" className="text-primary hover:text-primary/80">
              Privacy Policy
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function BasicContent() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isReady, user, isLoading } = useAuth();
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  // Redirect if already logged in
  React.useEffect(() => {
    if (isReady && user) {
      navigate("/dashboard", { replace: true });
    }
  }, [isReady, user, navigate]);

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoginError(null);
    setSubmitting(true);

    const form = e.currentTarget;
    const username = (form.elements.namedItem("username") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;

    setBasicAuth(username, password);

    try {
      await queryClient.fetchQuery({ queryKey: ["me"], queryFn: getMe });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      clearBasicAuth();
      const axiosError = err as AxiosError;
      if (axiosError?.response?.status === 401) {
        setLoginError("Invalid username or password.");
      } else {
        setLoginError(getApiErrorMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // Show login form (if already logged in, the useEffect above redirects)
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <div className="flex-1 flex items-center justify-center px-4 py-6">
        <div className="w-full max-w-md">
          <div className="text-center mb-6">
            <Link to="/" className="inline-flex items-center space-x-2">
              <TentTree className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold">camply</span>
            </Link>
            <p className="text-muted-foreground mt-1 text-sm">
              Never miss your perfect campsite
            </p>
          </div>

          <Card>
            <CardHeader className="text-center pb-4">
              <CardTitle className="text-xl">Sign In</CardTitle>
              <CardDescription className="text-sm">
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
                    disabled={submitting}
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
                    disabled={submitting}
                  />
                </div>
                {loginError && (
                  <p className="text-sm text-destructive">{loginError}</p>
                )}
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? "Signing in…" : "Sign In"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export function Auth() {
  const { authMode } = useAuth();

  if (authMode === "auth0") {
    return <Auth0Content />;
  }
  return <BasicContent />;
}
