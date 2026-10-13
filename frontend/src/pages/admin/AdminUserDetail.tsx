import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  Shield,
  User as UserIcon,
  Bell,
  Clock,
  Radio,
  ExternalLink,
  KeyRound,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { useAdminLocation } from "@/hooks/useAdminLocation";
import { getApiErrorMessage } from "@/lib/api";
import { AdminNav } from "@/components/AdminNav";
import {
  useAdminUser,
  useUpdateAdminUser,
  useAdminScans,
  useUpdateAdminScan,
} from "@/hooks/useAdmin";
import { useAuth } from "@/hooks/useAuth";

export function AdminUserDetail() {
  const { page, setPage } = useAdminLocation();
  const pageSize = 50;
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const { userId } = useParams<{ userId: string }>();
  const [updatingUser, setUpdatingUser] = useState(false);
  const [updatingScanId, setUpdatingScanId] = useState<string | null>(null);

  const [isResetPasswordOpen, setIsResetPasswordOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState("");
  const [resettingPassword, setResettingPassword] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const {
    data: user,
    isLoading: userLoading,
    error: userError,
    refetch: refetchUser,
  } = useAdminUser(userId || "");
  const {
    data: scansData,
    isLoading: scansLoading,
    error: scansError,
    refetch: refetchScans,
  } = useAdminScans({
    owner_id: userId,
    limit: pageSize,
    offset: page * pageSize,
  });

  const { user: currentUser, authMode } = useAuth();
  const updateUserMutation = useUpdateAdminUser();
  const updateScanMutation = useUpdateAdminScan();

  if (userLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <AdminNav />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (userError || !user) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <AdminNav />
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            User not found or error loading user
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3 mr-2"
            onClick={() => refetchUser()}
          >
            Retry
          </Button>
          <Button asChild variant="outline" size="sm" className="mt-3">
            <Link to="/admin/users">Back to Users</Link>
          </Button>
        </div>
      </div>
    );
  }

  const handleResetPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setResetError(null);
    try {
      setResettingPassword(true);
      await updateUserMutation.mutateAsync({
        userId: user.id,
        payload: {
          password: resetPassword,
          must_change_password: true,
        },
      });
      await refetchUser();
      setIsResetPasswordOpen(false);
      setResetPassword("");
      setMessage(
        `Temporary password set for ${user.email}. User must change it on their next sign-in.`,
      );
    } catch (error) {
      setResetError(getApiErrorMessage(error));
    } finally {
      setResettingPassword(false);
    }
  };

  const handleToggleAdmin = async () => {
    setMessage(null);
    setActionError(false);
    try {
      setUpdatingUser(true);
      await updateUserMutation.mutateAsync({
        userId: user.id,
        payload: { is_admin: !user.is_admin },
      });
      await refetchUser();
      setMessage(
        user.is_admin
          ? `Administrator privileges revoked for ${user.email}.`
          : `Administrator privileges granted to ${user.email}.`,
      );
    } catch (error) {
      setActionError(true);
      setMessage(getApiErrorMessage(error));
    } finally {
      setUpdatingUser(false);
    }
  };

  const handleToggleScanning = async () => {
    setMessage(null);
    setActionError(false);
    try {
      setUpdatingUser(true);
      await updateUserMutation.mutateAsync({
        userId: user.id,
        payload: { scanning_enabled: !user.scanning_enabled },
      });
      await refetchUser();
      setMessage(
        user.scanning_enabled
          ? "Scanning suspended. Login and saved scans are preserved."
          : "Scanning enabled.",
      );
    } catch (error) {
      setActionError(true);
      setMessage(getApiErrorMessage(error));
    } finally {
      setUpdatingUser(false);
    }
  };

  const handleToggleScanActive = async (scanId: string, current: boolean) => {
    setMessage(null);
    setActionError(false);
    try {
      setUpdatingScanId(scanId);
      await updateScanMutation.mutateAsync({
        scanId,
        payload: { is_active: !current },
      });
      setMessage(
        current ? "Scan paused." : "Scan resumed and eligible for checks.",
      );
    } catch (error) {
      setActionError(true);
      setMessage(getApiErrorMessage(error));
    } finally {
      setUpdatingScanId(null);
    }
  };

  const scans = scansData?.scans ?? [];

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-4">
        <Button asChild variant="ghost" size="sm" className="gap-1 mb-2">
          <Link to="/admin/users">
            <ArrowLeft className="h-4 w-4" /> Back to Users
          </Link>
        </Button>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              {user.email}
              {user.is_admin ? (
                <Badge variant="default" className="text-xs">
                  <Shield className="h-3 w-3 mr-1" /> Admin
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  <UserIcon className="h-3 w-3 mr-1" /> User
                </Badge>
              )}
              {user.must_change_password && (
                <Badge
                  variant="outline"
                  className="text-amber-600 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 text-xs"
                >
                  Password change required
                </Badge>
              )}
            </h1>
            <p className="text-xs font-mono text-muted-foreground mt-1">
              UUID: {user.id}
            </p>
          </div>
          {authMode === "session" && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setResetPassword("");
                  setResetError(null);
                  setIsResetPasswordOpen(true);
                }}
                className="gap-1.5"
              >
                <KeyRound className="h-4 w-4" /> Reset Password
              </Button>
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={isResetPasswordOpen}
        onOpenChange={(open) => {
          setIsResetPasswordOpen(open);
          if (!open) {
            setResetPassword("");
            setResetError(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a temporary password for {user.email}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="detail-reset-password">
                New Temporary Password
              </Label>
              <Input
                id="detail-reset-password"
                type="password"
                placeholder="Enter temporary password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
                disabled={resettingPassword}
              />
            </div>
            <div className="rounded-md bg-muted/60 p-3 text-xs text-muted-foreground">
              The user will be required to create a new password immediately
              upon their next sign-in.
            </div>

            {resetError && (
              <div
                role="alert"
                className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
              >
                {resetError}
              </div>
            )}

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsResetPasswordOpen(false)}
                disabled={resettingPassword}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={resettingPassword}>
                {resettingPassword ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Resetting…
                  </>
                ) : (
                  "Reset Password"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AdminNav />

      <AdminFeedback message={message} error={actionError} />
      {/* User Information & Suspension Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Account Profile & Status</CardTitle>
            <CardDescription>
              Account details and notification setup.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-muted-foreground block">
                  Email
                </span>
                <span className="font-medium">{user.email}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Auth0 ID
                </span>
                <span className="font-mono text-xs">
                  {user.auth0_id ?? "No Auth0 identity"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Invited User
                </span>
                <span>{user.is_invited ? "Yes" : "No"}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Password Change
                </span>
                <span>
                  {user.must_change_password ? (
                    <span className="text-amber-600 font-medium">
                      Required on sign in
                    </span>
                  ) : (
                    "Not required"
                  )}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Pushover Configured
                </span>
                <span className="flex items-center gap-1">
                  <Bell className="h-3.5 w-3.5 text-muted-foreground" />
                  {user.has_pushover_token ? "Yes (Token Set)" : "No"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Created At
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {new Date(user.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Updated At
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {new Date(user.updated_at).toLocaleString()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Permissions & Scanning Controls */}
        <div className="space-y-6">
          {/* Admin Role Card */}
          <Card
            className={`border-2 ${user.is_admin ? "border-primary/20" : "border-border"}`}
          >
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Administrator access</span>
                <Badge variant={user.is_admin ? "default" : "secondary"}>
                  {user.is_admin ? "Admin" : "Standard User"}
                </Badge>
              </CardTitle>
              <CardDescription>
                Administrator access grants permissions to manage users, modify
                scan configurations, and inspect operational telemetry.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg border bg-background">
                <div>
                  <p className="font-medium text-sm">Administrator Role</p>
                  <p className="text-xs text-muted-foreground">
                    {currentUser?.id === user.id
                      ? "You cannot remove your own administrator privileges"
                      : user.is_admin
                        ? "Full administrative access enabled"
                        : "Standard user access only"}
                  </p>
                </div>
                <Switch
                  aria-label={`Administrator privileges for ${user.email}`}
                  checked={user.is_admin}
                  disabled={updatingUser || currentUser?.id === user.id}
                  onCheckedChange={handleToggleAdmin}
                />
              </div>
            </CardContent>
          </Card>

          {/* Scanning Control Card */}
          <Card
            className={`border-2 ${user.scanning_enabled ? "border-emerald-500/20" : "border-amber-500/30 bg-amber-500/5"}`}
          >
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Scanning access</span>
                <Badge variant={user.scanning_enabled ? "success" : "warning"}>
                  {user.scanning_enabled ? "Enabled" : "Suspended"}
                </Badge>
              </CardTitle>
              <CardDescription>
                Suspension stops this user’s scans and new scan creation. Login
                and saved scan settings are preserved.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg border bg-background">
                <div>
                  <p className="font-medium text-sm">
                    Allow Automated Scanning
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {user.scanning_enabled
                      ? "Active scans are eligible for checks"
                      : "Suspended: scans will not run"}
                  </p>
                </div>
                <Switch
                  aria-label={`Scanning access for ${user.email}`}
                  checked={user.scanning_enabled}
                  disabled={updatingUser}
                  onCheckedChange={handleToggleScanning}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* User Scans */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Radio className="h-5 w-5 text-primary" /> User Scans (
          {user.total_scans})
        </h2>

        {scansLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : scansError ? (
          <div role="alert">
            Failed to load user scans.{" "}
            <Button onClick={() => refetchScans()}>Retry</Button>
          </div>
        ) : scans.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              This user has not created any campsite scans yet.
            </CardContent>
          </Card>
        ) : (
          <div className="rounded-md border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="py-3 px-4 text-left font-medium">
                      Campground
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Date Range
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Scan setting
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Eligible for checks
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Shared Target Campsites
                    </th>
                    <th className="py-3 px-4 text-right font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {scans.map((s) => {
                    const isUpdating = updatingScanId === s.id;
                    return (
                      <tr
                        key={s.id}
                        className="hover:bg-muted/30 transition-colors"
                      >
                        <td className="py-3 px-4">
                          <div className="font-medium">{s.campground_name}</div>
                          <div className="text-xs text-muted-foreground font-mono">
                            {s.provider_id === 1
                              ? "Recreation.gov"
                              : `Provider ${s.provider_id}`}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-xs">
                          {s.start_date} → {s.end_date}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <Switch
                              aria-label={`Saved active scan at ${s.campground_name}`}
                              checked={s.is_active}
                              disabled={
                                isUpdating ||
                                updateScanMutation.isPending ||
                                (!s.is_active && !user.scanning_enabled)
                              }
                              onCheckedChange={() =>
                                handleToggleScanActive(s.id, s.is_active)
                              }
                            />
                            <span className="text-xs">
                              {s.is_active ? "Active" : "Paused"}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {s.is_eligible ? (
                            <Badge variant="success" className="text-xs">
                              Eligible
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">
                              {s.user_scanning_enabled
                                ? "Scan paused"
                                : "Owner scanning suspended"}
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-4 font-medium">
                          {s.found_count}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Button asChild variant="ghost" size="sm">
                            <Link
                              to={`/admin/scans/${s.id}`}
                              className="inline-flex items-center gap-1"
                            >
                              Scan Details <ExternalLink className="h-3 w-3" />
                            </Link>
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {scansData && (
          <AdminPagination
            page={page}
            pageSize={pageSize}
            total={scansData.total}
            onPage={setPage}
          />
        )}
      </div>
    </div>
  );
}
