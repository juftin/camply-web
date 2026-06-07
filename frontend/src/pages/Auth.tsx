import * as React from "react";
import { TentTree } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { Header } from "@/components/Header";
import { useAuth } from "@/hooks/useAuth";

function Auth0Content() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithRedirect } = useAuth0();
  const { isReady, user, isEarlyAccess } = useAuth();
  const isSignUp = searchParams.get("mode") === "signup";

  // Redirect authenticated early-access users to dashboard.
  React.useEffect(() => {
    if (isReady && user && isEarlyAccess) {
      navigate("/dashboard", { replace: true });
    }
  }, [isReady, user, isEarlyAccess, navigate]);

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

function LocalContent() {
  const navigate = useNavigate();
  React.useEffect(() => {
    navigate("/dashboard", { replace: true });
  }, [navigate]);
  return null;
}

export function Auth() {
  const { authMode } = useAuth();

  if (authMode === "auth0") {
    return <Auth0Content />;
  }
  return <LocalContent />;
}
