import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, Target, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { AdminNav } from "@/components/AdminNav";
import { useAdminScans, useUpdateAdminScan } from "@/hooks/useAdmin";

export function AdminScans() {
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "paused">(
    "all",
  );
  const [eligibleFilter, setEligibleFilter] = useState<
    "all" | "eligible" | "ineligible"
  >("all");
  const [updatingScanId, setUpdatingScanId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isActiveParam =
    activeFilter === "all" ? undefined : activeFilter === "active";
  const isEligibleParam =
    eligibleFilter === "all" ? undefined : eligibleFilter === "eligible";

  const { data, isLoading, error, refetch } = useAdminScans({
    is_active: isActiveParam,
    is_eligible: isEligibleParam,
    limit: 100,
  });

  const updateScanMutation = useUpdateAdminScan();

  const handleToggleScan = async (
    scanId: string,
    current: boolean,
    userScanningEnabled: boolean,
  ) => {
    if (!current && !userScanningEnabled) {
      setErrorMessage(
        "Cannot resume scan: User scanning privileges are currently suspended.",
      );
      return;
    }
    setErrorMessage(null);
    try {
      setUpdatingScanId(scanId);
      await updateScanMutation.mutateAsync({
        scanId,
        payload: { is_active: !current },
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to toggle scan status";
      setErrorMessage(msg);
    } finally {
      setUpdatingScanId(null);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold">Scans Management</h1>
          <p className="text-muted-foreground mt-1">
            Global scan fleet, active status overrides, eligibility filters, and
            target links.
          </p>
        </div>
      </div>

      <AdminNav />

      {errorMessage && (
        <div className="mb-4 rounded-md bg-destructive/10 border border-destructive/30 p-3 text-destructive text-sm flex items-center justify-between">
          <span>{errorMessage}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setErrorMessage(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>Status:</span>
            <Button
              variant={activeFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("all")}
            >
              All
            </Button>
            <Button
              variant={activeFilter === "active" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("active")}
            >
              Active
            </Button>
            <Button
              variant={activeFilter === "paused" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("paused")}
            >
              Paused
            </Button>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span>Eligibility:</span>
            <Button
              variant={eligibleFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setEligibleFilter("all")}
            >
              All
            </Button>
            <Button
              variant={eligibleFilter === "eligible" ? "default" : "outline"}
              size="sm"
              onClick={() => setEligibleFilter("eligible")}
            >
              Eligible
            </Button>
            <Button
              variant={eligibleFilter === "ineligible" ? "default" : "outline"}
              size="sm"
              onClick={() => setEligibleFilter("ineligible")}
            >
              Ineligible
            </Button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error || !data ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load scan fleet
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
      ) : data.scans.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No scans found matching current filters.
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-md border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="py-3 px-4 text-left font-medium">Owner</th>
                  <th className="py-3 px-4 text-left font-medium">
                    Campground
                  </th>
                  <th className="py-3 px-4 text-left font-medium">Dates</th>
                  <th className="py-3 px-4 text-left font-medium">
                    Saved Active
                  </th>
                  <th className="py-3 px-4 text-left font-medium">
                    Eligibility
                  </th>
                  <th className="py-3 px-4 text-left font-medium">Target</th>
                  <th className="py-3 px-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.scans.map((s) => {
                  const isUpdating = updatingScanId === s.id;
                  return (
                    <tr
                      key={s.id}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <Link
                          to={`/admin/users/${s.user_id}`}
                          className="font-medium hover:underline text-foreground block"
                        >
                          {s.user_email}
                        </Link>
                        {!s.user_scanning_enabled && (
                          <Badge
                            variant="warning"
                            className="text-[10px] mt-0.5"
                          >
                            User Suspended
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-medium">{s.campground_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {s.provider_id === 1
                            ? "Recreation.gov"
                            : `Provider ${s.provider_id}`}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs whitespace-nowrap">
                        {s.start_date} → {s.end_date}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={s.is_active}
                            disabled={isUpdating}
                            onCheckedChange={() =>
                              handleToggleScan(
                                s.id,
                                s.is_active,
                                s.user_scanning_enabled,
                              )
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
                      <td className="py-3 px-4">
                        <Button
                          asChild
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                        >
                          <Link
                            to={`/admin/targets/${s.target_id}`}
                            className="gap-1"
                          >
                            <Target className="h-3 w-3 text-primary" /> Target
                          </Link>
                        </Button>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button asChild variant="ghost" size="sm">
                          <Link
                            to={`/admin/scans/${s.id}`}
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
              Showing {data.scans.length} of {data.total} scans
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
