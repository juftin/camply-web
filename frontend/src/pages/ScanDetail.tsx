import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar,
  Activity,
  Zap,
  Clock,
  ChevronLeft,
  Loader2,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScanForm } from "@/components/ScanForm";
import { FoundCampsites } from "@/components/FoundCampsites";
import { useScanDetail } from "@/hooks/useScans";
import { getCampground } from "@/lib/api";
import {
  toTitleCase,
  formatDate,
  daysBetween,
  formatRelativeTime,
  formatDisplayDate,
} from "@/lib/utils";

export function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const {
    data: scan,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useScanDetail(scanId ?? null);
  const { data: campground } = useQuery({
    queryKey: [
      "campground",
      scan ? String(scan.provider_id) : null,
      scan?.campground_id,
    ],
    queryFn: () => getCampground(scan!.provider_id, scan!.campground_id),
    enabled: !!scan,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center justify-center min-h-[40vh]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!scan) {
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
            <Button
              className="mt-3"
              disabled={isFetching}
              onClick={() => refetch()}
            >
              Try again
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
          {toTitleCase(
            scan.campground_name ||
              scan.recreation_area_name ||
              "Unknown Campground",
          )}
        </h1>
        {scan.recreation_area_name && scan.campground_name && (
          <p className="text-muted-foreground mt-1">
            {toTitleCase(scan.recreation_area_name)}
          </p>
        )}
        {campground?.url && (
          <a
            href={campground.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 inline-flex min-h-11 items-center gap-1.5 text-sm text-primary hover:underline"
          >
            View campground on provider
            <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
          </a>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant={scan.is_active ? "success" : "secondary"}>
            {scan.is_active ? "Monitoring" : "Paused"}
          </Badge>
          <span>
            {formatDisplayDate(scan.start_date, false)} –{" "}
            {formatDisplayDate(scan.end_date, false)}
          </span>
          <span>· {scan.min_stay_length}+ nights</span>
          {(scan.preferred_types ?? []).length > 0 && (
            <span>· {scan.preferred_types.join(", ")}</span>
          )}
          {scan.require_electric && <span>· Electric required</span>}
        </div>
      </div>

      <div className="mb-6">
        <ScanForm scan={scan} />
      </div>

      <div className="grid gap-6">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            Could not refresh availability. Showing the last loaded results.{" "}
            <Button
              variant="outline"
              size="sm"
              disabled={isFetching}
              onClick={() => refetch()}
            >
              Try again
            </Button>
          </p>
        )}
        <FoundCampsites key={scan.id} scan={scan} />
        {/* Overview */}
        <details className="group rounded-lg border bg-card text-card-foreground shadow-sm">
          <summary className="flex cursor-pointer list-none items-center gap-3 rounded-lg p-5 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
            <ChevronRight
              aria-hidden="true"
              className="h-3.5 w-3.5 text-muted-foreground transition-transform group-open:rotate-90"
            />
            Scan overview
            <span className="ml-auto hidden text-xs font-normal text-muted-foreground sm:inline">
              Dates, preferences & monitoring details
            </span>
          </summary>
          <div className="space-y-4 p-6 pt-0">
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
          </div>
        </details>
      </div>
    </div>
  );
}
