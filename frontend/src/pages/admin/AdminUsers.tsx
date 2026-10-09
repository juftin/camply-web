import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Loader2,
  Shield,
  User as UserIcon,
  ExternalLink,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { AdminNav } from "@/components/AdminNav";
import { useAdminUsers, useUpdateAdminUser } from "@/hooks/useAdmin";

export function AdminUsers() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "enabled" | "suspended">("all");
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);

  const scanningEnabledParam =
    filter === "all" ? undefined : filter === "enabled";

  const { data, isLoading, error, refetch } = useAdminUsers({
    search: search.trim() || undefined,
    scanning_enabled: scanningEnabledParam,
    limit: 100,
  });

  const updateMutation = useUpdateAdminUser();

  const handleToggleScanning = async (userId: string, current: boolean) => {
    try {
      setUpdatingUserId(userId);
      await updateMutation.mutateAsync({
        userId,
        payload: { scanning_enabled: !current },
      });
    } catch {
      // Error handled by mutation
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
            Search users, toggle scanning suspension privileges, and inspect
            scans.
          </p>
        </div>
      </div>

      <AdminNav />

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by email or user ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={filter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("all")}
          >
            All
          </Button>
          <Button
            variant={filter === "enabled" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("enabled")}
          >
            Scanning Enabled
          </Button>
          <Button
            variant={filter === "suspended" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("suspended")}
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
                    Scanning Privileges
                  </th>
                  <th className="py-3 px-4 text-left font-medium">
                    Scans (Total / Active)
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
                        {u.is_admin ? (
                          <Badge variant="default" className="gap-1">
                            <Shield className="h-3 w-3" /> Admin
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="gap-1">
                            <UserIcon className="h-3 w-3" /> User
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={u.scanning_enabled}
                            disabled={isUpdating}
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
                        <Button asChild variant="ghost" size="sm">
                          <Link
                            to={`/admin/users/${u.id}`}
                            className="inline-flex items-center gap-1"
                          >
                            Details <ExternalLink className="h-3 w-3" />
                          </Link>
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="p-3 border-t bg-muted/20 text-xs text-muted-foreground flex justify-between items-center">
            <span>
              Showing {data.users.length} of {data.total} users
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
