import { Link } from "react-router-dom";
import {
  Users,
  Radio,
  Target,
  AlertTriangle,
  Loader2,
  Clock,
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
import { AdminNav } from "@/components/AdminNav";
import { AdminTrendsPanel } from "@/components/admin/AdminTrendsPanel";
import { useAdminOverview, useAdminOperations } from "@/hooks/useAdmin";

export function AdminOverview() {
  const { data, isLoading, error, refetch } = useAdminOverview();
  const { data: operations } = useAdminOperations();

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <h1 className="text-3xl font-bold mb-2">Administration</h1>
        <AdminNav />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <h1 className="text-3xl font-bold mb-2">Administration</h1>
        <AdminNav />
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load system overview
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
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold">Administration</h1>
          <p className="text-muted-foreground mt-1">
            Manage scanning access and review scan activity and system health.
          </p>
        </div>
      </div>

      <AdminNav />

      {data.overdue_targets > 0 && (
        <div className="mb-6 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-950/20 p-4 text-amber-900 dark:text-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <p className="font-semibold text-sm">
                {data.overdue_targets} Target
                {data.overdue_targets > 1 ? "s" : ""} Overdue for Checking
              </p>
              <p className="text-xs text-amber-800 dark:text-amber-300">
                These shared targets are eligible for checks but have not been
                checked within the overdue threshold (
                {data.overdue_threshold_seconds}
                s).
              </p>
            </div>
          </div>
          <Button
            asChild
            variant="outline"
            size="sm"
            className="border-amber-500/50"
          >
            <Link to="/admin/scans?target_status=overdue">
              View scans with overdue targets
            </Link>
          </Button>
        </div>
      )}

      {/* User Metrics */}
      <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
        <Users className="h-5 w-5 text-primary" /> Users
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Users</CardDescription>
            <CardTitle className="text-3xl">{data.total_users}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to="/admin/users"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              View all users <ExternalLink className="h-3 w-3" />
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Scanning Enabled</CardDescription>
            <CardTitle className="text-3xl text-emerald-600 dark:text-emerald-400">
              {data.scanning_enabled_users}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Users allowed to create and run scans
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Scanning Suspended</CardDescription>
            <CardTitle
              className={`text-3xl ${data.suspended_users > 0 ? "text-amber-600 dark:text-amber-400" : ""}`}
            >
              {data.suspended_users}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Login is allowed; scans and new scan creation are suspended
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Scan Metrics */}
      <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
        <Radio className="h-5 w-5 text-primary" /> User Scans
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Saved Scans</CardDescription>
            <CardTitle className="text-3xl">{data.total_scans}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to="/admin/scans"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1"
            >
              Explore scan list <ExternalLink className="h-3 w-3" />
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Scans Set to Active</CardDescription>
            <CardTitle className="text-3xl">
              {data.saved_active_scans}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Includes active scans of suspended users
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Scans Eligible for Checks</CardDescription>
            <CardTitle className="text-3xl text-primary">
              {data.eligible_scans}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Active scans whose owners have scanning access
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Target Discovery Metrics */}
      <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
        <Target className="h-5 w-5 text-primary" /> Shared Targets
      </h2>
      <p className="text-sm text-muted-foreground mb-3">
        A target is one provider, campground, and date range shared by matching
        scans. Eligible targets have at least one active scan whose owner has
        scanning access. Dormant targets have none. Overdue targets are a subset
        of eligible targets.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Unique Targets</CardDescription>
            <CardTitle className="text-2xl">{data.total_targets}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Eligible for checks</CardDescription>
            <CardTitle className="text-2xl text-emerald-600 dark:text-emerald-400">
              {data.eligible_targets}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Dormant Targets</CardDescription>
            <CardTitle className="text-2xl text-muted-foreground">
              {data.dormant_targets}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Overdue Targets</CardDescription>
            <CardTitle
              className={`text-2xl ${data.overdue_targets > 0 ? "text-amber-600 dark:text-amber-400 font-bold" : ""}`}
            >
              {data.overdue_targets}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Historical Trend Graphs */}
      {operations?.capabilities?.historical_trends === false ? (
        <p className="mb-6 text-sm text-muted-foreground">
          Historical trends are disabled in standalone mode.
        </p>
      ) : operations ? (
        <AdminTrendsPanel
          group="usage"
          title="User and Scan Trends"
          description="User registrations, saved scans, shared availability checks, and campground searches over time."
        />
      ) : null}

      {/* Configuration & Worker Timing */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" /> Availability
            Check Timing
          </CardTitle>
          <CardDescription>
            The scheduler finds targets ready for a check. Each target waits at
            least the cooldown period between checks.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between items-center p-3 rounded-lg border bg-muted/30">
            <span className="text-muted-foreground">Scheduler Interval</span>
            <Badge variant="outline">{data.heartbeat_interval_seconds}s</Badge>
          </div>
          <div className="flex justify-between items-center p-3 rounded-lg border bg-muted/30">
            <span className="text-muted-foreground">
              Minimum Time Between Checks
            </span>
            <Badge variant="outline">{data.target_cooldown_seconds}s</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
