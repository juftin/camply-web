// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import { useState } from "react";
import { User, TentTree, Mail, Bell, LogOut, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
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
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage } from "@/lib/api";

export function Profile() {
  const {
    user,
    isEarlyAccess,
    isLoading,
    updatePushoverToken,
    signOut,
  } = useAuth();
  const navigate = useNavigate();

  const [pushoverToken, setPushoverToken] = useState(user?.pushover_token ?? "");
  const [pushoverSaving, setPushoverSaving] = useState(false);
  const [pushoverError, setPushoverError] = useState<string | null>(null);
  const [pushoverSuccess, setPushoverSuccess] = useState(false);

  const handleSavePushover = async () => {
    setPushoverSaving(true);
    setPushoverError(null);
    setPushoverSuccess(false);
    try {
      await updatePushoverToken(pushoverToken || null);
      setPushoverSuccess(true);
      setTimeout(() => setPushoverSuccess(false), 3000);
    } catch (err) {
      setPushoverError(getApiErrorMessage(err));
    } finally {
      setPushoverSaving(false);
    }
  };

  const handleSignOut = () => {
    signOut();
    navigate("/");
  };

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
          <User className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Profile</h1>
          <p className="text-muted-foreground text-sm">
            Manage your account settings
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {/* Account Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TentTree className="h-5 w-5 text-primary" />
              Account
            </CardTitle>
            <CardDescription>
              Your account details and status
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">{user.email}</p>
                <p className="text-xs text-muted-foreground">Email</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-4 w-4 text-muted-foreground" />
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">Early Access</p>
                {isEarlyAccess ? (
                  <Badge
                    variant="outline"
                    className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800"
                  >
                    Active
                  </Badge>
                ) : (
                  <Badge variant="secondary">Pending</Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Pushover Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              Notifications
            </CardTitle>
            <CardDescription>
              Configure your Pushover integration for real-time campsite alerts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="pushover_token">Pushover User Key</Label>
              <Input
                id="pushover_token"
                placeholder="Enter your Pushover user key"
                value={pushoverToken}
                onChange={(e) => setPushoverToken(e.target.value)}
              />
            </div>
            <Button
              onClick={handleSavePushover}
              disabled={pushoverSaving}
            >
              {pushoverSaving ? "Saving..." : "Save"}
            </Button>
            {pushoverError && (
              <p className="text-sm text-destructive">{pushoverError}</p>
            )}
            {pushoverSuccess && (
              <p className="text-sm text-green-600">Pushover token saved!</p>
            )}
            <p className="text-xs text-muted-foreground">
              Don't have a Pushover key?{" "}
              <a
                href="https://pushover.net/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                Sign up at pushover.net
              </a>
            </p>
          </CardContent>
        </Card>

        {/* Sign Out */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <LogOut className="h-5 w-5 text-destructive" />
              Sign Out
            </CardTitle>
            <CardDescription>
              Sign out of your camply account
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="destructive"
              onClick={handleSignOut}
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sign Out
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
