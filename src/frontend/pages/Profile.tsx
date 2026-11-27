import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import {
  Loader2,
  LogOut,
  Mail,
  ArrowLeft,
  LayoutDashboard,
} from "lucide-react";
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
import { NotificationSettings } from "@/components/NotificationSettings";
import { ActiveSessions } from "@/components/ActiveSessions";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage } from "@/lib/api";

export function Profile() {
  const { user, isLoading, refresh, signOut, authMode, autoLogin } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-muted-foreground">Not signed in</p>
      </div>
    );
  }

  const handleSignOut = async () => {
    setSignOutError(null);
    setSigningOut(true);
    try {
      await signOut();
      navigate("/", { replace: true });
    } catch (error) {
      setSignOutError(getApiErrorMessage(error));
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="flex items-center gap-2 mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Home
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Profile</CardTitle>
          <CardDescription>
            Manage your account and notification preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="min-w-0 break-words space-y-6">
          {/* Email */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              Email
            </Label>
            <Input value={user.email} disabled />
            <p className="text-xs text-muted-foreground">
              Your email is managed through your authentication provider.
            </p>
          </div>

          <NotificationSettings key={user.id} user={user} refresh={refresh} />

          {authMode === "session" &&
            !autoLogin &&
            !user.must_change_password && <ActiveSessions />}

          {/* Actions */}
          <div className="pt-4 border-t space-y-3">
            <Button
              variant="outline"
              className="min-h-11 w-full sm:min-h-0"
              asChild
            >
              <Link to="/dashboard">
                <LayoutDashboard className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Link>
            </Button>

            {!autoLogin && (
              <Button
                variant="destructive"
                className="min-h-11 w-full sm:min-h-0"
                onClick={handleSignOut}
                disabled={signingOut}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            )}
            {signOutError && (
              <p role="alert" className="text-sm text-destructive">
                {signOutError}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
