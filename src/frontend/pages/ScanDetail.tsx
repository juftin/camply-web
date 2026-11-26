import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Accessibility,
  Calendar,
  ChevronLeft,
  Clock,
  ExternalLink,
  Loader2,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScanForm } from "@/components/ScanForm";
import { FoundCampsites } from "@/components/FoundCampsites";
import { CoverageSummary } from "@/components/found-campsites/CoverageSummary";
import { useScanDetail } from "@/hooks/useScans";
import { getCampground, getRecreationArea } from "@/lib/api";
import { formatAllowedWeekdays } from "@/lib/weekdays";
import {
  toTitleCase,
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
      scan?.destination_type ?? "campground",
      scan ? String(scan.provider_id) : null,
      scan?.recreation_area_id ?? scan?.campground_id,
    ],
    queryFn: () =>
      scan!.destination_type === "recreation_area"
        ? getRecreationArea(scan!.provider_id, scan!.recreation_area_id!)
        : getCampground(scan!.provider_id, scan!.campground_id!),
    enabled: !!scan,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <div className="flex min-h-[40vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="container mx-auto max-w-5xl px-4 py-8">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <h2 className="mb-2 text-xl font-semibold">Scan Not Found</h2>
            <p className="mb-4 text-muted-foreground">
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
  const isEnded = new Date(scan.end_date) < new Date();
  const lastChecked = scan.last_checked_at
    ? formatRelativeTime(scan.last_checked_at)
    : "Not checked yet";

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <Button
        variant="ghost"
        size="sm"
        className="mb-4 -ml-2"
        onClick={() => navigate("/dashboard")}
      >
        <ChevronLeft className="mr-1 h-4 w-4" />
        Back to Dashboard
      </Button>

      {/* Cohesive Scan Header */}
      <header className="mb-6 rounded-lg border bg-card p-5 text-card-foreground shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="break-words text-2xl font-bold sm:text-3xl">
                {toTitleCase(
                  scan.destination_name ||
                    scan.campground_name ||
                    scan.recreation_area_name ||
                    "Unknown Campground",
                )}
              </h1>
              <Badge variant={scan.is_active ? "success" : "secondary"}>
                {scan.is_active ? "Monitoring" : "Paused"}
              </Badge>
              {isEnded && <Badge variant="warning">Ended</Badge>}
            </div>

            {scan.recreation_area_name && scan.campground_name && (
              <p className="text-sm text-muted-foreground">
                {toTitleCase(scan.recreation_area_name)}
              </p>
            )}

            {campground?.url && (
              <a
                href={campground.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-11 items-center sm:min-h-9 gap-1.5 text-sm font-medium text-primary hover:underline"
              >
                {scan.destination_type === "recreation_area"
                  ? "View recreation area on provider"
                  : "View campground on provider"}
                <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
              </a>
            )}
          </div>

          <div className="shrink-0">
            <ScanForm scan={scan} />
          </div>
        </div>

        {/* Dates, freshness, and saved criteria */}
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-4 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 text-foreground">
            <Calendar
              aria-hidden="true"
              className="h-4 w-4 shrink-0 text-muted-foreground"
            />
            {formatDisplayDate(scan.start_date, false)} –{" "}
            {formatDisplayDate(scan.end_date, false)}{" "}
            <span className="text-muted-foreground">
              ({daysDiff} night{daysDiff !== 1 ? "s" : ""})
            </span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Clock aria-hidden="true" className="h-4 w-4 shrink-0" />
            Last checked: {lastChecked}
          </span>
          <span>Created {formatRelativeTime(scan.created_at)}</span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary">
            Min {scan.min_stay_length} night
            {scan.min_stay_length !== 1 ? "s" : ""}
          </Badge>
          <Badge variant="secondary">
            {formatAllowedWeekdays(scan.allowed_weekdays)}
          </Badge>
          {scan.require_electric && (
            <Badge variant="secondary" className="gap-1">
              <Zap aria-hidden="true" className="h-3 w-3" />
              Electric required
            </Badge>
          )}
          {scan.require_accessible && (
            <Badge variant="secondary" className="gap-1">
              <Accessibility aria-hidden="true" className="h-3 w-3" />
              ADA accessible
            </Badge>
          )}
          {scan.min_rv_length != null && (
            <Badge variant="secondary">Min {scan.min_rv_length} ft</Badge>
          )}
          {(scan.preferred_types ?? []).length > 0 && (
            <Badge variant="secondary">
              Types: {(scan.preferred_types ?? []).join(", ")}
            </Badge>
          )}
        </div>
      </header>

      {scan.destination_type === "recreation_area" && (
        <CoverageSummary scan={scan} />
      )}

      {error && (
        <div
          role="alert"
          className="mb-6 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <span>
            Could not refresh availability. Showing the last loaded results.
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={isFetching}
            onClick={() => refetch()}
          >
            Try again
          </Button>
        </div>
      )}

      <FoundCampsites key={scan.id} scan={scan} />
    </div>
  );
}
