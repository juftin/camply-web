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
import { AdminNav } from "@/components/AdminNav";
import {
  useAdminUser,
  useUpdateAdminUser,
  useAdminScans,
  useUpdateAdminScan,
} from "@/hooks/useAdmin";

export function AdminUserDetail() {
  const { userId } = useParams<{ userId: string }>();
  const [updatingUser, setUpdatingUser] = useState(false);
  const [updatingScanId, setUpdatingScanId] = useState<string | null>(null);

  const {
    data: user,
    isLoading: userLoading,
    error: userError,
    refetch: refetchUser,
  } = useAdminUser(userId || "");
  const { data: scansData, isLoading: scansLoading } = useAdminScans({
    owner_id: userId,
    limit: 100,
  });

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
          <Button asChild variant="outline" size="sm" className="mt-3">
            <Link to="/admin/users">Back to Users</Link>
          </Button>
        </div>
      </div>
    );
  }

  const handleToggleScanning = async () => {
    try {
      setUpdatingUser(true);
      await updateUserMutation.mutateAsync({
        userId: user.id,
        payload: { scanning_enabled: !user.scanning_enabled },
      });
      await refetchUser();
    } finally {
      setUpdatingUser(false);
    }
  };

  const handleToggleScanActive = async (scanId: string, current: boolean) => {
    try {
      setUpdatingScanId(scanId);
      await updateScanMutation.mutateAsync({
        scanId,
        payload: { is_active: !current },
      });
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
            </h1>
            <p className="text-xs font-mono text-muted-foreground mt-1">
              UUID: {user.id}
            </p>
          </div>
        </div>
      </div>

      <AdminNav />

      {/* User Information & Suspension Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Account Profile & Status</CardTitle>
            <CardDescription>
              User metadata and authentication status.
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
                  {user.auth0_id ?? "Local / Password"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Early Access User
                </span>
                <span>{user.is_invited ? "Yes" : "No"}</span>
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

        {/* Scanning Control Card */}
        <Card
          className={`border-2 ${user.scanning_enabled ? "border-emerald-500/20" : "border-amber-500/30 bg-amber-500/5"}`}
        >
          <CardHeader>
            <CardTitle className="text-lg flex items-center justify-between">
              <span>Scanning Privilege</span>
              <Badge variant={user.scanning_enabled ? "success" : "warning"}>
                {user.scanning_enabled ? "Enabled" : "Suspended"}
              </Badge>
            </CardTitle>
            <CardDescription>
              Suspended users retain their login and scans, but background
              pollers will skip their requests.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border bg-background">
              <div>
                <p className="font-medium text-sm">Allow Automated Scanning</p>
                <p className="text-xs text-muted-foreground">
                  {user.scanning_enabled
                    ? "User scans are polled by workers"
                    : "Suspended: worker skips scans"}
                </p>
              </div>
              <Switch
                checked={user.scanning_enabled}
                disabled={updatingUser}
                onCheckedChange={handleToggleScanning}
              />
            </div>
          </CardContent>
        </Card>
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
                      Saved Active
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Effective Eligible
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Found Sites
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
                              checked={s.is_active}
                              disabled={
                                isUpdating ||
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
                              Ineligible
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
      </div>
    </div>
  );
}
