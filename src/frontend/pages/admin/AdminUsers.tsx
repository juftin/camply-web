import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Loader2,
  Shield,
  User as UserIcon,
  ExternalLink,
  UserPlus,
  KeyRound,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { AdminNav } from "@/components/AdminNav";
import { useAdminLocation } from "@/hooks/useAdminLocation";
import { AdminPagination } from "@/components/admin/AdminPagination";
import { AdminFeedback } from "@/components/admin/AdminFeedback";
import { AdminPasswordInput } from "@/components/admin/AdminPasswordInput";
import { getApiErrorMessage } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import {
  useAdminUsers,
  useCreateAdminUser,
  useUpdateAdminUser,
} from "@/hooks/useAdmin";
import type { AdminUserItem } from "@/lib/structs";

export function AdminUsers() {
  const { authMode } = useAuth();
  const { params, page, update, setPage } = useAdminLocation();
  const search = params.get("search") ?? "";
  const filter = params.get("status") ?? "all";
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const pageSize = 50;
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [newMustChangePassword, setNewMustChangePassword] = useState(true);
  const [newScanningEnabled, setNewScanningEnabled] = useState(true);
  const [createError, setCreateError] = useState<string | null>(null);

  const [resetUser, setResetUser] = useState<AdminUserItem | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resettingPassword, setResettingPassword] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);

  const scanningEnabledParam =
    filter === "all" ? undefined : filter === "enabled";

  const { data, isLoading, error, refetch } = useAdminUsers({
    search: search.trim() || undefined,
    scanning_enabled: scanningEnabledParam,
    limit: pageSize,
    offset: page * pageSize,
  });

  const createMutation = useCreateAdminUser();
  const updateMutation = useUpdateAdminUser();

  const handleCreateOpenChange = (open: boolean) => {
    setIsCreateOpen(open);
    if (!open) {
      setNewPassword("");
      setCreateError(null);
    }
  };

  const handleCreateUser = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreateError(null);
    try {
      await createMutation.mutateAsync({
        email: newEmail.trim().toLowerCase(),
        password: newPassword,
        is_admin: newIsAdmin,
        must_change_password: newMustChangePassword,
        scanning_enabled: newScanningEnabled,
        is_invited: true,
      });
      setIsCreateOpen(false);
      setNewEmail("");
      setNewPassword("");
      setNewIsAdmin(false);
      setNewMustChangePassword(true);
      setNewScanningEnabled(true);
      setMessage(`User ${newEmail} created successfully.`);
    } catch (err) {
      setCreateError(getApiErrorMessage(err));
    }
  };

  const handleResetPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!resetUser) return;
    setResetError(null);
    try {
      setResettingPassword(true);
      await updateMutation.mutateAsync({
        userId: resetUser.id,
        payload: {
          password: resetPassword,
          must_change_password: true,
        },
      });
      const targetEmail = resetUser.email;
      setResetUser(null);
      setResetPassword("");
      setMessage(
        `Temporary password set for ${targetEmail}. User must change it on their next sign-in.`,
      );
    } catch (err) {
      setResetError(getApiErrorMessage(err));
    } finally {
      setResettingPassword(false);
    }
  };

  const handleToggleScanning = async (userId: string, current: boolean) => {
    setMessage(null);
    setActionError(false);
    try {
      setUpdatingUserId(userId);
      await updateMutation.mutateAsync({
        userId,
        payload: { scanning_enabled: !current },
      });
      setMessage(
        current
          ? "Scanning suspended. Login and saved scans are preserved."
          : "Scanning enabled.",
      );
    } catch (error) {
      setActionError(true);
      setMessage(getApiErrorMessage(error));
    } finally {
      setUpdatingUserId(null);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground mt-1">
            Find users, enable or suspend scanning access, and inspect their
            scans. Suspension preserves login and saved scans, and prevents new
            scans.
          </p>
        </div>
        {authMode === "session" && (
          <Button
            onClick={() => setIsCreateOpen(true)}
            className="gap-2 shrink-0"
          >
            <UserPlus className="h-4 w-4" />
            Create User
          </Button>
        )}
      </div>

      <Dialog open={isCreateOpen} onOpenChange={handleCreateOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create User</DialogTitle>
            <DialogDescription>
              Create a new user with session credentials.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="create-email">Email</Label>
              <Input
                id="create-email"
                type="email"
                placeholder="user@example.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
                disabled={createMutation.isPending}
              />
            </div>
            {isCreateOpen && (
              <AdminPasswordInput
                id="create-password"
                label="Initial Password"
                value={newPassword}
                onChange={setNewPassword}
                disabled={createMutation.isPending}
              />
            )}
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <Label htmlFor="create-is-admin" className="cursor-pointer">
                  Admin Privileges
                </Label>
                <Switch
                  id="create-is-admin"
                  checked={newIsAdmin}
                  onCheckedChange={setNewIsAdmin}
                  disabled={createMutation.isPending}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label
                    htmlFor="create-must-change"
                    className="cursor-pointer block"
                  >
                    Force password change on first sign in
                  </Label>
                  <span className="text-xs text-muted-foreground">
                    User must change this password after signing in
                  </span>
                </div>
                <Switch
                  id="create-must-change"
                  checked={newMustChangePassword}
                  onCheckedChange={setNewMustChangePassword}
                  disabled={createMutation.isPending}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label
                  htmlFor="create-scanning-enabled"
                  className="cursor-pointer"
                >
                  Scanning Enabled
                </Label>
                <Switch
                  id="create-scanning-enabled"
                  checked={newScanningEnabled}
                  onCheckedChange={setNewScanningEnabled}
                  disabled={createMutation.isPending}
                />
              </div>
            </div>

            {createError && (
              <div
                role="alert"
                className="rounded-md bg-destructive/10 p-3 text-sm text-destructive"
              >
                {createError}
              </div>
            )}

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleCreateOpenChange(false)}
                disabled={createMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating…
                  </>
                ) : (
                  "Create User"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!resetUser}
        onOpenChange={(open) => {
          if (!open) {
            setResetUser(null);
            setResetPassword("");
            setResetError(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a temporary password for {resetUser?.email}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResetPassword} className="space-y-4">
            {resetUser && (
              <AdminPasswordInput
                id="row-reset-password"
                label="New Temporary Password"
                value={resetPassword}
                onChange={setResetPassword}
                disabled={resettingPassword}
              />
            )}
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
                onClick={() => {
                  setResetUser(null);
                  setResetPassword("");
                  setResetError(null);
                }}
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

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by email or user ID..."
            value={search}
            onChange={(e) => update({ search: e.target.value })}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={filter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => update({ status: "all" })}
          >
            All
          </Button>
          <Button
            variant={filter === "enabled" ? "default" : "outline"}
            size="sm"
            onClick={() => update({ status: "enabled" })}
          >
            Scanning Enabled
          </Button>
          <Button
            variant={filter === "suspended" ? "default" : "outline"}
            size="sm"
            onClick={() => update({ status: "suspended" })}
          >
            Suspended
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error || !data ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load user list
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </div>
      ) : data.users.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No users found matching your search criteria.
          </CardContent>
          <AdminPagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPage={setPage}
          />
        </Card>
      ) : (
        <div className="rounded-md border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="py-3 px-4 text-left font-medium">User</th>
                  <th className="py-3 px-4 text-left font-medium">Role</th>
                  <th className="py-3 px-4 text-left font-medium">
                    Scanning access
                  </th>
                  <th className="py-3 px-4 text-left font-medium">
                    Scans (Total / Set to Active)
                  </th>
                  <th className="py-3 px-4 text-left font-medium">Joined</th>
                  <th className="py-3 px-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.users.map((u) => {
                  const isUpdating = updatingUserId === u.id;
                  return (
                    <tr
                      key={u.id}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-medium text-foreground">
                          {u.email}
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                          {u.id}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-col items-start gap-1">
                          {u.is_admin ? (
                            <Badge variant="default" className="gap-1">
                              <Shield className="h-3 w-3" /> Admin
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="gap-1">
                              <UserIcon className="h-3 w-3" /> User
                            </Badge>
                          )}
                          {u.must_change_password && (
                            <Badge
                              variant="outline"
                              className="text-amber-600 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 text-[10px] py-0 px-1.5"
                            >
                              Password change required
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Switch
                            aria-label={`Scanning access for ${u.email}`}
                            checked={u.scanning_enabled}
                            disabled={isUpdating || updateMutation.isPending}
                            onCheckedChange={() =>
                              handleToggleScanning(u.id, u.scanning_enabled)
                            }
                          />
                          <span
                            className={`text-xs font-medium ${
                              u.scanning_enabled
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-amber-600 dark:text-amber-400"
                            }`}
                          >
                            {u.scanning_enabled ? "Enabled" : "Suspended"}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium">{u.total_scans}</span>{" "}
                        total (
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                          {u.active_scans} active
                        </span>
                        )
                      </td>
                      <td className="py-3 px-4 text-muted-foreground text-xs">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {authMode === "session" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setResetUser(u);
                                setResetPassword("");
                                setResetError(null);
                              }}
                              className="gap-1 text-muted-foreground hover:text-foreground"
                              aria-label={`Reset password for ${u.email}`}
                            >
                              <KeyRound className="h-3.5 w-3.5" />
                              Reset
                            </Button>
                          )}
                          <Button asChild variant="ghost" size="sm">
                            <Link
                              to={`/admin/users/${u.id}`}
                              className="inline-flex items-center gap-1"
                            >
                              Details <ExternalLink className="h-3 w-3" />
                            </Link>
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <AdminPagination
            page={page}
            pageSize={pageSize}
            total={data.total}
            onPage={setPage}
          />
        </div>
      )}
    </div>
  );
}
