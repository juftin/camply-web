import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Layers,
  Loader2,
  RefreshCw,
  Server,
  Zap,
} from "lucide-react";
import { useAdminLocation } from "@/hooks/useAdminLocation";
import { AdminNav } from "@/components/AdminNav";
import { AdminTrendsPanel } from "@/components/admin/AdminTrendsPanel";
import { taskLabel } from "@/components/admin/labels";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAdminOperations, useAdminOperationsTasks } from "@/hooks/useAdmin";
import type { AdminTaskTelemetryItem } from "@/lib/structs";

export function AdminOperations() {
  const { params, page, update, setPage } = useAdminLocation();
  const outcomeFilter = params.get("outcome") ?? "all";
  const taskNameFilter = params.get("task_name") ?? "";
  const tab = params.get("tab");
  const activeTrendsTab = tab === "api" || tab === "provider" ? tab : "worker";
  const [selectedTask, setSelectedTask] =
    useState<AdminTaskTelemetryItem | null>(null);
  const pageSize = 20;

  const {
    data: opsData,
    isLoading: isOpsLoading,
    error: opsError,
    refetch: refetchOps,
    isFetching: isOpsFetching,
  } = useAdminOperations();

  const {
    data: tasksData,
    isLoading: isTasksLoading,
    error: tasksError,
    refetch: refetchTasks,
    isFetching: isTasksFetching,
  } = useAdminOperationsTasks({
    limit: pageSize,
    offset: page * pageSize,
    outcome: outcomeFilter === "all" ? undefined : outcomeFilter,
    task_name: taskNameFilter.trim() || undefined,
  });

  const handleRefresh = () => {
    refetchOps();
    refetchTasks();
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) {
      return `${Math.round(ms)} ms`;
    }
    return `${(ms / 1000).toFixed(2)} s`;
  };

  const formatTimestamp = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const getOutcomeBadge = (outcome: string) => {
    const norm = outcome.toLowerCase();
    switch (norm) {
      case "success":
        return <Badge className="bg-green-600 text-white">Success</Badge>;
      case "error":
      case "failure":
        return <Badge variant="destructive">Error</Badge>;
      case "retrying":
        return <Badge className="bg-amber-500 text-white">Retrying</Badge>;
      case "skipped":
        return <Badge variant="secondary">Skipped</Badge>;
      default:
        return <Badge variant="outline">{outcome}</Badge>;
    }
  };

  const renderEntityLink = (
    entityType: string | null | undefined,
    entityId: string | null | undefined,
  ) => {
    if (!entityType || !entityId)
      return <span className="text-muted-foreground">-</span>;
    let href = "";
    if (entityType.toLowerCase() === "target")
      href = `/admin/targets/${entityId}`;
    else if (entityType.toLowerCase() === "user")
      href = `/admin/users/${entityId}`;
    else if (entityType.toLowerCase() === "scan")
      href = `/admin/scans/${entityId}`;

    if (href) {
      return (
        <Link
          to={href}
          className="inline-flex items-center gap-1 text-primary hover:underline font-mono text-xs"
        >
          {entityType}: {entityId.slice(0, 8)}…
          <ExternalLink className="h-3 w-3" />
        </Link>
      );
    }
    return (
      <span className="font-mono text-xs">
        {entityType}: {entityId.slice(0, 8)}…
      </span>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold">System Operations</h1>
          <p className="text-muted-foreground mt-1">
            Read-only worker status, queued tasks, scheduling activity, and
            recent task results. Data refreshes every 15 seconds.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isOpsFetching || isTasksFetching}
            className="flex items-center gap-2"
          >
            <RefreshCw
              className={`h-4 w-4 ${isOpsFetching || isTasksFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      <AdminNav />

      {/* Freshness and connection indicator */}
      <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-muted/40 rounded-lg border text-sm mb-6">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-muted-foreground">
              Task Queue:
            </span>
            {opsData?.broker_connected ? (
              <Badge className="bg-emerald-600 text-white flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Connected
              </Badge>
            ) : (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> Disconnected
              </Badge>
            )}
          </div>
          {opsData?.snapshot_at && (
            <div className="text-xs text-muted-foreground">
              Checked at: {formatTimestamp(opsData.snapshot_at)}
            </div>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          Auto-refreshes every 15s • Read-only inspection
        </div>
      </div>

      {opsError && (
        <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm mb-6 flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold">
              Operations inspection unavailable
            </div>
            <div>
              {opsError instanceof Error
                ? opsError.message
                : "Failed to connect to operations endpoint or Celery broker."}
            </div>
          </div>
        </div>
      )}

      {opsData?.stale && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm"
        >
          {opsData.error_message}. Displaying last known values where available.
          Last complete snapshot:{" "}
          {opsData.last_successful_at
            ? formatTimestamp(opsData.last_successful_at)
            : "None"}
          .{" "}
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            Retry
          </Button>
        </div>
      )}
      {/* Top workload summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Queued Tasks
            </CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isOpsLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">
                {(opsData?.telemetry_available === false &&
                  !opsData.last_successful_at) ||
                !opsData
                  ? "Unavailable"
                  : opsData.queue_depth}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Waiting for a worker to pick them up
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Running Tasks
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isOpsLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">
                {(opsData?.inspection_available === false &&
                  !opsData.last_successful_at) ||
                !opsData
                  ? "Unavailable"
                  : opsData.active_tasks_total}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Currently running
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Reserved Tasks
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isOpsLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">
                {(opsData?.inspection_available === false &&
                  !opsData.last_successful_at) ||
                !opsData
                  ? "Unavailable"
                  : opsData.reserved_tasks_total}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Picked up by workers; waiting to run
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Worker Nodes
            </CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isOpsLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <div className="text-2xl font-bold">
                {opsData?.workers?.length ?? 0}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              {opsData?.scheduled_tasks_total ?? 0} scheduled tasks
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Discovery Metadata & Worker Nodes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Latest Scheduling Run Card */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              Latest Scheduling Run
            </CardTitle>
          </CardHeader>
          <CardContent>
            {opsData?.last_discovery ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">Status:</span>
                  <Badge variant="outline" className="font-semibold capitalize">
                    {opsData.last_discovery.status}
                  </Badge>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">
                    Targets Ready for Checks:
                  </span>
                  <span className="font-bold">
                    {opsData.last_discovery.targets_discovered}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">
                    Checks Added to Queue:
                  </span>
                  <span className="font-bold">
                    {opsData.last_discovery.targets_enqueued}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-muted-foreground">Last Executed:</span>
                  <span className="text-xs font-mono">
                    {formatTimestamp(opsData.last_discovery.timestamp)}
                  </span>
                </div>
                <div className="mt-4 pt-3 border-t text-xs text-muted-foreground">
                  The scheduler finds targets ready for checks and queues them.
                  The timestamp shows when the last run completed.
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground py-4 text-center">
                No scheduling run has been recorded yet.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Worker Nodes Table */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4 text-primary" />
              Workers
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isOpsLoading ? (
              <div className="flex justify-center py-6">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !opsData?.workers || opsData.workers.length === 0 ? (
              <div className="p-4 text-center text-muted-foreground text-sm border rounded-lg bg-muted/20">
                No worker nodes actively responding to inspection. Worker
                processes may be offline.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <p className="text-xs text-muted-foreground mb-3">
                  Running tasks are executing. Reserved tasks wait to run.
                  Scheduled tasks wait for a future start time.
                </p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground text-xs font-medium">
                      <th className="pb-2">Worker Node</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2 text-right">Running</th>
                      <th className="pb-2 text-right">Reserved</th>
                      <th className="pb-2 text-right">Scheduled</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {opsData.workers.map((worker) => (
                      <tr key={worker.name} className="hover:bg-muted/30">
                        <td className="py-2.5 font-mono text-xs">
                          {worker.name}
                        </td>
                        <td className="py-2.5">
                          <Badge
                            className={
                              worker.status === "online"
                                ? "bg-emerald-600 text-white"
                                : "bg-amber-500 text-white"
                            }
                          >
                            {worker.status}
                          </Badge>
                        </td>
                        <td className="py-2.5 text-right font-medium">
                          {worker.active_tasks}
                        </td>
                        <td className="py-2.5 text-right text-muted-foreground">
                          {worker.reserved_tasks}
                        </td>
                        <td className="py-2.5 text-right text-muted-foreground">
                          {worker.scheduled_tasks}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Operational Trends Section (Worker, API, Provider) */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              System Performance Trends
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Review task results, API traffic, and booking provider
              availability checks over time.
            </p>
          </div>
          <div className="flex items-center space-x-1 border rounded-md p-1 bg-muted/40">
            {(
              [
                { id: "worker", label: "Workers" },
                { id: "api", label: "API" },
                { id: "provider", label: "Booking Providers" },
              ] as const
            ).map((t) => (
              <Button
                key={t.id}
                size="sm"
                variant={activeTrendsTab === t.id ? "default" : "ghost"}
                className="h-7 text-xs px-3"
                onClick={() => update({ tab: t.id }, false)}
              >
                {t.label}
              </Button>
            ))}
          </div>
        </div>

        {activeTrendsTab === "worker" && (
          <AdminTrendsPanel
            group="worker"
            title="Worker and Task Trends"
            description="Task volume, completion results, execution time, and shared-target scheduling."
          />
        )}

        {activeTrendsTab === "api" && (
          <AdminTrendsPanel
            group="api"
            title="API Traffic and Response Times"
            description="Requests per second by API route, response status, and how long requests take."
          />
        )}

        {activeTrendsTab === "provider" && (
          <AdminTrendsPanel
            group="provider"
            title="Booking Provider Trends"
            description="Availability checks and errors reported when contacting booking providers."
          />
        )}
      </div>

      {/* Recent Task Executions Section */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Recent Task Results
              </CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Up to 1,000 recent task records, retained for up to 24 hours.
                Sensitive task arguments are hidden.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                placeholder="Filter task name..."
                value={taskNameFilter}
                onChange={(e) => {
                  update({ task_name: e.target.value });
                }}
                className="w-44 h-8 text-xs"
              />
              <div className="flex items-center space-x-1">
                {(
                  ["all", "success", "error", "skipped", "retrying"] as const
                ).map((out) => (
                  <Button
                    key={out}
                    size="sm"
                    variant={outcomeFilter === out ? "default" : "outline"}
                    className="h-8 text-xs px-2.5 capitalize"
                    onClick={() => {
                      update({ outcome: out });
                    }}
                  >
                    {out}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isTasksLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : tasksError || tasksData?.available === false ? (
            <div className="p-4 text-center text-sm text-destructive">
              {tasksData?.error_message ||
                "Failed to load recent task results."}{" "}
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetchTasks()}
              >
                Retry
              </Button>
            </div>
          ) : !tasksData?.tasks || tasksData.tasks.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No recent task results match these filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground text-xs font-medium">
                    <th className="pb-2">Task</th>
                    <th className="pb-2">Worker</th>
                    <th className="pb-2">Related Record</th>
                    <th className="pb-2">Finished At</th>
                    <th className="pb-2 text-right">Duration</th>
                    <th className="pb-2">Outcome</th>
                    <th className="pb-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {tasksData.tasks.map((task) => (
                    <tr key={task.task_id} className="hover:bg-muted/30">
                      <td className="py-2.5">
                        <div className="font-mono text-xs font-medium">
                          {taskLabel(task.task_name)}
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          {task.task_id.slice(0, 8)}…
                        </div>
                      </td>
                      <td className="py-2.5 font-mono text-xs text-muted-foreground">
                        {task.worker}
                      </td>
                      <td className="py-2.5">
                        {renderEntityLink(task.entity_type, task.entity_id)}
                      </td>
                      <td className="py-2.5 text-xs text-muted-foreground">
                        {formatTimestamp(task.finished_at)}
                      </td>
                      <td className="py-2.5 text-right font-mono text-xs">
                        {formatDuration(task.duration_ms)}
                      </td>
                      <td className="py-2.5">
                        {getOutcomeBadge(task.outcome)}
                      </td>
                      <td className="py-2.5 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs px-2"
                          onClick={() => setSelectedTask(task)}
                        >
                          Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t mt-4 text-xs text-muted-foreground">
                <div>
                  Showing {page * pageSize + 1} -{" "}
                  {Math.min((page + 1) * pageSize, tasksData.total)} of{" "}
                  {tasksData.total}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={page === 0}
                    onClick={() => setPage(Math.max(0, page - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={(page + 1) * pageSize >= tasksData.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Task Details Dialog */}
      <Dialog
        open={Boolean(selectedTask)}
        onOpenChange={(open) => {
          if (!open) setSelectedTask(null);
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">
              Task Execution Details
            </DialogTitle>
            <DialogDescription className="text-xs">
              Allowlisted metadata recorded by the worker lifecycle listener.
            </DialogDescription>
          </DialogHeader>

          {selectedTask && (
            <div className="space-y-3 py-2 text-sm">
              <div className="flex justify-between items-start border-b pb-2">
                <span className="text-muted-foreground text-xs">Task ID:</span>
                <span className="font-mono text-xs break-all text-right max-w-[240px]">
                  {selectedTask.task_id}
                </span>
              </div>
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-muted-foreground text-xs">
                  Task Name:
                </span>
                <span className="font-mono text-xs text-right">
                  {selectedTask.task_name}
                </span>
              </div>
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-muted-foreground text-xs">
                  Worker Node:
                </span>
                <span className="font-mono text-xs text-right">
                  {selectedTask.worker}
                </span>
              </div>
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-muted-foreground text-xs">Outcome:</span>
                <span>{getOutcomeBadge(selectedTask.outcome)}</span>
              </div>
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-muted-foreground text-xs">Duration:</span>
                <span className="font-mono text-xs">
                  {formatDuration(selectedTask.duration_ms)}
                </span>
              </div>
              <div className="flex justify-between items-center border-b pb-2">
                <span className="text-muted-foreground text-xs">
                  Finished At:
                </span>
                <span className="text-xs">
                  {formatTimestamp(selectedTask.finished_at)}
                </span>
              </div>
              {selectedTask.entity_type && (
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-muted-foreground text-xs">Entity:</span>
                  <span>
                    {renderEntityLink(
                      selectedTask.entity_type,
                      selectedTask.entity_id,
                    )}
                  </span>
                </div>
              )}
              {selectedTask.reason && (
                <div className="border-b pb-2">
                  <div className="text-muted-foreground text-xs mb-1">
                    Reason:
                  </div>
                  <div className="font-mono text-xs p-2 bg-muted rounded border text-muted-foreground">
                    {selectedTask.reason}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
