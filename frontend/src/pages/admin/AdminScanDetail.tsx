import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2, Calendar, Clock, Target, Zap } from "lucide-react";
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
import { useAdminScan, useUpdateAdminScan } from "@/hooks/useAdmin";

export function AdminScanDetail() {
  const { scanId } = useParams<{ scanId: string }>();
  const [updating, setUpdating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: scan, isLoading, error, refetch } = useAdminScan(scanId || "");
  const updateScanMutation = useUpdateAdminScan();

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <AdminNav />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <AdminNav />
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Scan not found or error loading scan
          </p>
          <Button asChild variant="outline" size="sm" className="mt-3">
            <Link to="/admin/scans">Back to Scans</Link>
          </Button>
        </div>
      </div>
    );
  }

  const handleToggleActive = async () => {
    setErrorMessage(null);
    if (!scan.is_active && !scan.user_scanning_enabled) {
      setErrorMessage(
        "Cannot resume scan: User scanning privileges are currently suspended.",
      );
      return;
    }
    try {
      setUpdating(true);
      await updateScanMutation.mutateAsync({
        scanId: scan.id,
        payload: { is_active: !scan.is_active },
      });
      await refetch();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to toggle scan status";
      setErrorMessage(msg);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-4">
        <Button asChild variant="ghost" size="sm" className="gap-1 mb-2">
          <Link to="/admin/scans">
            <ArrowLeft className="h-4 w-4" /> Back to Scans
          </Link>
        </Button>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              {scan.campground_name}
            </h1>
            <p className="text-xs font-mono text-muted-foreground mt-1">
              Scan UUID: {scan.id}
            </p>
          </div>
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

      {/* Scan Overview & Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Scan Configuration</CardTitle>
            <CardDescription>
              Subscriber parameters and target linkage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-muted-foreground block">
                  Subscriber Account
                </span>
                <Link
                  to={`/admin/users/${scan.user_id}`}
                  className="font-medium text-primary hover:underline"
                >
                  {scan.user_email}
                </Link>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Shared Target
                </span>
                <Link
                  to={`/admin/targets/${scan.target_id}`}
                  className="font-mono text-xs text-primary hover:underline flex items-center gap-1"
                >
                  <Target className="h-3 w-3" /> {scan.target_id.slice(0, 8)}...
                </Link>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Dates
                </span>
                <span className="flex items-center gap-1 font-medium">
                  <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                  {scan.start_date} → {scan.end_date}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Stay Requirement
                </span>
                <span>Minimum {scan.min_stay_length} night(s)</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Electric Hookup
                </span>
                <span className="flex items-center gap-1">
                  <Zap className="h-3.5 w-3.5 text-muted-foreground" />
                  {scan.require_electric ? "Required" : "Any"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Preferred Types
                </span>
                <span>
                  {scan.preferred_types.length > 0
                    ? scan.preferred_types.join(", ")
                    : "All"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Last Checked
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {scan.last_checked_at
                    ? new Date(scan.last_checked_at).toLocaleString()
                    : "Never"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Created At
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {new Date(scan.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* State and Status Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Execution State</CardTitle>
            <CardDescription>
              Saved user preference vs worker polling eligibility.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg border bg-background">
              <div>
                <p className="font-medium text-sm">Saved Active</p>
                <p className="text-xs text-muted-foreground">
                  User toggle preference
                </p>
              </div>
              <Switch
                checked={scan.is_active}
                disabled={updating}
                onCheckedChange={handleToggleActive}
              />
            </div>

            <div className="p-3 rounded-lg border bg-muted/20 space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">
                  User Scanning Privileges
                </span>
                {scan.user_scanning_enabled ? (
                  <Badge variant="success" className="text-[10px]">
                    Enabled
                  </Badge>
                ) : (
                  <Badge variant="warning" className="text-[10px]">
                    Suspended
                  </Badge>
                )}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">
                  Effective Eligibility
                </span>
                {scan.is_eligible ? (
                  <Badge variant="success" className="text-[10px]">
                    Polled by Worker
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-[10px]">
                    Skipped
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Available Campsites Found */}
      <div>
        <h2 className="text-xl font-semibold mb-4">
          Latest Found Campsites ({scan.results.length})
        </h2>
        {scan.results.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No matching available campsites currently found for this target.
            </CardContent>
          </Card>
        ) : (
          <div className="rounded-md border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="py-3 px-4 text-left font-medium">
                      Campsite ID
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Campsite Name
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Available Dates
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {scan.results.map((r, i) => (
                    <tr
                      key={`${r.campsite_id}-${i}`}
                      className="hover:bg-muted/30"
                    >
                      <td className="py-3 px-4 font-mono text-xs">
                        {r.campsite_id}
                      </td>
                      <td className="py-3 px-4 font-medium">
                        {r.campsite_name || "Campsite"}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {r.available_dates.map((date) => (
                            <Badge
                              key={date}
                              variant="outline"
                              className="text-xs"
                            >
                              {date}
                            </Badge>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
