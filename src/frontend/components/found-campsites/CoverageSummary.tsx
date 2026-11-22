import { AlertTriangle, ChevronRight, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ScanDetailResponse } from "@/lib/structs";
import { formatRelativeTime } from "@/lib/utils";

export interface CoverageSummaryProps {
  scan: ScanDetailResponse;
}

function memberStatusBadge(eligible: boolean, outcome: string) {
  if (!eligible) {
    return <Badge variant="secondary">Unavailable</Badge>;
  }
  switch (outcome) {
    case "success":
      return <Badge variant="success">Checked</Badge>;
    case "failed":
      return <Badge variant="destructive">Failed</Badge>;
    default:
      return <Badge variant="warning">Pending</Badge>;
  }
}

/** Structured recreation-area campground coverage summary with expandable member details. */
export function CoverageSummary({ scan }: CoverageSummaryProps) {
  const modeLabel =
    scan.coverage_mode === "all" ? "All campgrounds" : "Selected campgrounds";
  const eligibleCount = scan.eligible_campground_count ?? 0;
  const checkedCount = scan.checked_campground_count ?? 0;
  const pendingCount = scan.pending_campground_count ?? 0;
  const failedCount = scan.failed_campground_count ?? 0;
  const unavailableCount = scan.unavailable_selection_count ?? 0;
  const isIncomplete = scan.coverage_status !== "complete";
  const members = scan.campgrounds ?? [];

  return (
    <section
      aria-label="Campground coverage"
      className="mb-6 rounded-lg border bg-card p-4 text-card-foreground shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Layers
            aria-hidden="true"
            className="h-4 w-4 text-muted-foreground"
          />
          <h2 className="text-sm font-semibold">{modeLabel}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <Badge variant="secondary">{eligibleCount} eligible</Badge>
          <Badge variant="success">{checkedCount} checked</Badge>
          {pendingCount > 0 && (
            <Badge variant="warning">{pendingCount} pending</Badge>
          )}
          {failedCount > 0 && (
            <Badge variant="destructive">{failedCount} failed</Badge>
          )}
          {unavailableCount > 0 && (
            <Badge variant="outline">{unavailableCount} unavailable</Badge>
          )}
        </div>
      </div>

      {isIncomplete && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-50/70 px-3 py-2 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertTriangle
            aria-hidden="true"
            className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400"
          />
          <p>
            Results may be incomplete; some campgrounds are unchecked or failed.
          </p>
        </div>
      )}

      {members.length > 0 && (
        <details className="group mt-3 border-t pt-2.5">
          <summary className="flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
            <ChevronRight
              aria-hidden="true"
              className="h-3.5 w-3.5 transition-transform group-open:rotate-90"
            />
            Campground status details ({members.length})
          </summary>
          <ul className="mt-2.5 divide-y rounded-md border bg-muted/20">
            {members.map((member) => (
              <li
                key={`${member.provider_id}:${member.campground_id}`}
                className="flex flex-col gap-1.5 px-3 py-2.5 text-xs sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="font-medium text-foreground">
                    {member.campground_name}
                  </p>
                  {!member.eligible && member.unavailable_reason && (
                    <p className="mt-0.5 text-muted-foreground">
                      {member.unavailable_reason}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  {member.last_checked_at && (
                    <span className="text-muted-foreground">
                      Checked {formatRelativeTime(member.last_checked_at)}
                    </span>
                  )}
                  {memberStatusBadge(member.eligible, member.outcome)}
                </div>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
