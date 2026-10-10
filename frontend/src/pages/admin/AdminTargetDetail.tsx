import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  Calendar,
  Clock,
  Radio,
  ExternalLink,
  Target as TargetIcon,
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
import { useAdminTarget } from "@/hooks/useAdmin";

export function AdminTargetDetail() {
  const { targetId } = useParams<{ targetId: string }>();

  const {
    data: target,
    isLoading,
    error,
    refetch,
  } = useAdminTarget(targetId || "");

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

  if (error || !target) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <AdminNav />
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Target not found or error loading target
          </p>
          <div className="flex justify-center gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link to="/admin/scans">Back to Scans</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "eligible":
        return <Badge variant="success">Eligible (Active Polling)</Badge>;
      case "overdue":
        return <Badge variant="destructive">Overdue for Poll</Badge>;
      case "dormant":
      default:
        return (
          <Badge variant="secondary">Dormant (No Eligible Subscribers)</Badge>
        );
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
              <TargetIcon className="h-7 w-7 text-primary" />{" "}
              {target.campground_name}
            </h1>
            <p className="text-xs font-mono text-muted-foreground mt-1">
              Target UUID: {target.id}
            </p>
          </div>
          <div>{getStatusBadge(target.status)}</div>
        </div>
      </div>

      <AdminNav />

      {/* Target Properties */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">
              De-duplicated Poller Target
            </CardTitle>
            <CardDescription>
              Single underlying check shared across multiple subscribers.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-muted-foreground block">
                  Provider
                </span>
                <span>
                  {target.provider_id === 1
                    ? "Recreation.gov"
                    : `Provider ${target.provider_id}`}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Campground ID
                </span>
                <span className="font-mono text-xs">
                  {target.campground_id}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Date Window
                </span>
                <span className="flex items-center gap-1 font-medium">
                  <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                  {target.start_date} → {target.end_date}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Unique Target Hash
                </span>
                <span
                  className="font-mono text-xs truncate block"
                  title={target.hash}
                >
                  {target.hash}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Last Polled
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {target.last_checked_at
                    ? new Date(target.last_checked_at).toLocaleString()
                    : "Never"}
                </span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">
                  Created At
                </span>
                <span className="flex items-center gap-1 text-xs">
                  <Clock className="h-3 w-3 text-muted-foreground" />
                  {new Date(target.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscriber Count Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Subscribers</CardTitle>
            <CardDescription>De-duplication fan-out summary.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-3 rounded-lg border bg-background flex justify-between items-center">
              <span className="text-sm font-medium">Total Subscribers</span>
              <span className="text-2xl font-bold">
                {target.total_subscribers}
              </span>
            </div>
            <div className="p-3 rounded-lg border bg-muted/20 flex justify-between items-center">
              <div>
                <p className="text-sm font-medium">Eligible Subscribers</p>
                <p className="text-xs text-muted-foreground">
                  Active + user not suspended
                </p>
              </div>
              <span className="text-2xl font-bold text-primary">
                {target.eligible_subscribers}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Subscriber List */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <Radio className="h-5 w-5 text-primary" /> Attached Subscribers (
          {target.subscribers.length})
        </h2>

        {target.subscribers.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No subscribers attached to this target.
            </CardContent>
          </Card>
        ) : (
          <div className="rounded-md border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="py-3 px-4 text-left font-medium">
                      User Email
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Saved Active
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      User Status
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Eligible
                    </th>
                    <th className="py-3 px-4 text-left font-medium">
                      Subscribed Date
                    </th>
                    <th className="py-3 px-4 text-right font-medium">
                      Scan Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {target.subscribers.map((s) => (
                    <tr key={s.scan_id} className="hover:bg-muted/30">
                      <td className="py-3 px-4">
                        <Link
                          to={`/admin/users/${s.user_id}`}
                          className="font-medium text-foreground hover:underline"
                        >
                          {s.user_email}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={s.is_active ? "outline" : "secondary"}
                          className="text-xs"
                        >
                          {s.is_active ? "Active" : "Paused"}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        {s.user_scanning_enabled ? (
                          <Badge variant="success" className="text-xs">
                            Enabled
                          </Badge>
                        ) : (
                          <Badge variant="warning" className="text-xs">
                            Suspended
                          </Badge>
                        )}
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
                      <td className="py-3 px-4 text-xs text-muted-foreground">
                        {new Date(s.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button asChild variant="ghost" size="sm">
                          <Link
                            to={`/admin/scans/${s.scan_id}`}
                            className="gap-1"
                          >
                            Scan <ExternalLink className="h-3 w-3" />
                          </Link>
                        </Button>
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
