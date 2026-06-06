import { useParams, useNavigate } from "react-router-dom";
import {
  Calendar,
  Activity,
  Zap,
  Clock,
  ChevronLeft,
  Loader2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useScanDetail } from "@/hooks/useScans";
import { toTitleCase } from "@/lib/utils";

function formatDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function daysBetween(start: string, end: string): number {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  return Math.max(0, Math.round((e.getTime() - s.getTime()) / 86400000));
}

function formatRelativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

export function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { data: scan, isLoading, error } = useScanDetail(scanId ?? null);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center justify-center min-h-[40vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <h2 className="text-xl font-semibold mb-2">Scan Not Found</h2>
            <p className="text-muted-foreground mb-4">
              The scan you're looking for could not be found.
            </p>
            <Button variant="outline" onClick={() => navigate("/dashboard")}>
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const daysDiff = daysBetween(scan.start_date, scan.end_date);
  const lastChecked = scan.last_checked_at
    ? formatRelativeTime(scan.last_checked_at)
    : "Never";

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Button
        variant="ghost"
        size="sm"
        className="mb-4"
        onClick={() => navigate("/dashboard")}
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Back to Dashboard
      </Button>

      <div className="mb-6">
        <h1 className="text-3xl font-bold">
          {toTitleCase(scan.campground_name || scan.recreation_area_name || "Unknown Campground")}
        </h1>
        {scan.recreation_area_name && scan.campground_name && (
          <p className="text-muted-foreground mt-1">
            {toTitleCase(scan.recreation_area_name)}
          </p>
        )}
      </div>

      <div className="grid gap-6">
        {/* Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Scan Overview</CardTitle>
            <CardDescription>Details about this monitor</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant={scan.is_active ? "success" : "secondary"}>
                {scan.is_active ? "Active" : "Paused"}
              </Badge>
              {new Date(scan.end_date) < new Date() && (
                <Badge variant="warning">Ended</Badge>
              )}
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground shrink-0" />
                <span>
                  <span className="text-muted-foreground">Dates: </span>
                  {formatDate(scan.start_date)} – {formatDate(scan.end_date)}{" "}
                  <span className="text-muted-foreground">
                    ({daysDiff} night{daysDiff !== 1 ? "s" : ""})
                  </span>
                </span>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Activity className="h-4 w-4 text-primary shrink-0" />
                <span>
                  <span className="text-muted-foreground">Sites found: </span>
                  <strong>{scan.found_count}</strong>
                </span>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                <span>
                  <span className="text-muted-foreground">Last checked: </span>
                  {lastChecked}
                </span>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                <span>
                  <span className="text-muted-foreground">Created: </span>
                  {formatRelativeTime(scan.created_at)}
                </span>
              </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-2 pt-2 border-t">
              {scan.require_electric && (
                <Badge variant="secondary" className="gap-1">
                  <Zap className="h-3 w-3" /> Electric Required
                </Badge>
              )}
              {scan.min_stay_length > 1 && (
                <Badge variant="secondary">
                  Min {scan.min_stay_length} nights
                </Badge>
              )}
              {(scan.preferred_types ?? []).length > 0 && (
                <Badge variant="secondary">
                  Types: {(scan.preferred_types ?? []).join(", ")}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Results</CardTitle>
            <CardDescription>
              Campsites found matching your criteria
            </CardDescription>
          </CardHeader>
          <CardContent>
            {(scan.results ?? []).length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                No results yet. Check back soon — the scanner runs periodically.
              </p>
            ) : (
              <div className="divide-y">
                {(scan.results ?? []).map((result) => (
                  <div
                    key={result.campsite_id}
                    className="py-3 first:pt-0 last:pb-0"
                  >
                    <p className="font-medium text-sm">
                      {result.campsite_name || result.campsite_id}
                    </p>
                    {result.available_dates.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {result.available_dates.map((date) => (
                          <Badge
                            key={date}
                            variant="outline"
                            className="text-xs"
                          >
                            {date}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
