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
import { useAdminOverview } from "@/hooks/useAdmin";

export function AdminOverview() {
  const { data, isLoading, error, refetch } = useAdminOverview();

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
            System health, active scans, user suspension controls, and targets.
          </p>
        </div>
      </div>

      <AdminNav />

      {data.overdue_targets > 0 && (
        <div className="mb-6 rounded-lg border border-amber-500/50 bg-amber-50 dark:bg-amber-950/20 p-4 text-amber-900 dark:text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <div>
              <p className="font-semibold text-sm">
                {data.overdue_targets} Target
                {data.overdue_targets > 1 ? "s" : ""} Overdue for Checking
              </p>
              <p className="text-xs text-amber-800 dark:text-amber-300">
                Targets have active subscribers but have not been evaluated
                within the cooldown window ({data.target_cooldown_seconds}s).
              </p>
            </div>
          </div>
          <Button
            asChild
            variant="outline"
            size="sm"
            className="border-amber-500/50"
          >
            <Link to="/admin/scans">Inspect Scans</Link>
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
              Active scanning privileges
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Suspended Users</CardDescription>
            <CardTitle
              className={`text-3xl ${data.suspended_users > 0 ? "text-amber-600 dark:text-amber-400" : ""}`}
            >
              {data.suspended_users}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Excluded from poll runs
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
            <CardDescription>Total Scans Configured</CardDescription>
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
            <CardDescription>Saved Active (User Setting)</CardDescription>
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
            <CardDescription>Effective Eligible Scans</CardDescription>
            <CardTitle className="text-3xl text-primary">
              {data.eligible_scans}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              Active + user enabled (polled)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Target Discovery Metrics */}
      <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
        <Target className="h-5 w-5 text-primary" /> Unique Poller Targets
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Unique Targets</CardDescription>
            <CardTitle className="text-2xl">{data.unique_targets}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Eligible (Polled)</CardDescription>
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
      <AdminTrendsPanel
        group="usage"
        title="Fleet Growth & Usage Trends"
        description="Historical user registrations, scan creation, activity, polling demand, and search throughput."
      />

      {/* Configuration & Worker Timing */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" /> Worker Polling
            Cadence
          </CardTitle>
          <CardDescription>
            Configured poller intervals controlling de-duplicated target
            discovery and cooldowns.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between items-center p-3 rounded-lg border bg-muted/30">
            <span className="text-muted-foreground">Heartbeat Interval</span>
            <Badge variant="outline">{data.heartbeat_interval_seconds}s</Badge>
          </div>
          <div className="flex justify-between items-center p-3 rounded-lg border bg-muted/30">
            <span className="text-muted-foreground">
              Target Cooldown Threshold
            </span>
            <Badge variant="outline">{data.target_cooldown_seconds}s</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
