import { useNavigate, Link } from "react-router-dom";
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
import { useAuth } from "@/hooks/useAuth";

export function Profile() {
  const { user, isLoading, refresh, signOut, autoLogin } = useAuth();
  const navigate = useNavigate();

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

  const handleSignOut = () => {
    signOut();
    navigate("/", { replace: true });
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
        <CardContent className="space-y-6">
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

          {/* Actions */}
          <div className="pt-4 border-t space-y-3">
            <Button variant="outline" className="w-full" asChild>
              <Link to="/dashboard">
                <LayoutDashboard className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Link>
            </Button>

            {!autoLogin && (
              <Button
                variant="destructive"
                className="w-full"
                onClick={handleSignOut}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
