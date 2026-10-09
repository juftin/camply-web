import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, History, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { AdminNav } from "@/components/AdminNav";
import { useAdminAudit } from "@/hooks/useAdmin";

export function AdminAudit() {
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const { data, isLoading, error, refetch } = useAdminAudit({ limit, offset });

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <History className="h-7 w-7 text-primary" /> Admin Audit Log
          </h1>
          <p className="text-muted-foreground mt-1">
            Immutable log of administrator privilege alterations, user
            suspensions, and scan state overrides.
          </p>
        </div>
      </div>

      <AdminNav />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error || !data ? (
        <div className="rounded-md bg-destructive/10 p-6 text-center">
          <p className="text-destructive font-medium">
            Failed to load audit records
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
      ) : data.events.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No audit events recorded yet.
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-md border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="py-3 px-4 text-left font-medium">Timestamp</th>
                  <th className="py-3 px-4 text-left font-medium">
                    Administrator
                  </th>
                  <th className="py-3 px-4 text-left font-medium">Action</th>
                  <th className="py-3 px-4 text-left font-medium">Subject</th>
                  <th className="py-3 px-4 text-left font-medium">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.events.map((e) => (
                  <tr key={e.id} className="hover:bg-muted/30">
                    <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium">{e.actor_email}</span>
                      <span className="block text-[10px] font-mono text-muted-foreground">
                        {e.actor_id}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="font-mono text-xs">
                        {e.action}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium capitalize">
                        {e.subject_type}:{" "}
                      </span>
                      {e.subject_type === "user" ? (
                        <Link
                          to={`/admin/users/${e.subject_id}`}
                          className="font-mono text-xs text-primary hover:underline"
                        >
                          {e.subject_id.slice(0, 8)}...
                        </Link>
                      ) : (
                        <Link
                          to={`/admin/scans/${e.subject_id}`}
                          className="font-mono text-xs text-primary hover:underline"
                        >
                          {e.subject_id.slice(0, 8)}...
                        </Link>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="inline-flex items-center gap-1.5 text-xs font-mono">
                        <Badge
                          variant={e.prev_value ? "success" : "secondary"}
                          className="text-[10px]"
                        >
                          {String(e.prev_value)}
                        </Badge>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <Badge
                          variant={e.new_value ? "success" : "secondary"}
                          className="text-[10px]"
                        >
                          {String(e.new_value)}
                        </Badge>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-3 border-t bg-muted/20 text-xs text-muted-foreground flex justify-between items-center">
            <span>
              Showing {data.events.length} of {data.total} audit events
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + limit >= data.total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
