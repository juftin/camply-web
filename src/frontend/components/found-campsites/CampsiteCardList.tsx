import { useState } from "react";
import {
  Accessibility,
  AlertTriangle,
  Caravan,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Ruler,
  Tent,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  MAX_INITIAL_STAYS,
  SITES_PER_PAGE,
  formatStayDate,
  stayKey,
  type FilteredFoundSite,
  type NormalizedFoundSite,
} from "@/lib/availability";
import { cn, formatRelativeTime } from "@/lib/utils";

/** Structured capability badges shared by campsite cards and the Grid stay inspector. */
export function SiteCapabilities({ site }: { site: NormalizedFoundSite }) {
  const hasCapabilities = Boolean(
    site.campsiteType ||
    site.isElectric ||
    site.isAccessible ||
    site.maxVehicleLength != null ||
    site.permittedEquipment.length > 0,
  );
  if (!hasCapabilities) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {site.campsiteType && (
        <Badge variant="secondary" className="gap-1 font-normal">
          <Tent aria-hidden="true" className="h-3 w-3" />
          {site.campsiteType}
        </Badge>
      )}
      {site.isElectric && (
        <Badge variant="secondary" className="gap-1 font-normal">
          <Zap aria-hidden="true" className="h-3 w-3" />
          Electric hookup
        </Badge>
      )}
      {site.isAccessible && (
        <Badge variant="secondary" className="gap-1 font-normal">
          <Accessibility aria-hidden="true" className="h-3 w-3" />
          Accessible
        </Badge>
      )}
      {site.maxVehicleLength != null && (
        <Badge variant="secondary" className="gap-1 font-normal">
          <Ruler aria-hidden="true" className="h-3 w-3" />
          Up to {site.maxVehicleLength} ft
        </Badge>
      )}
      {site.permittedEquipment.length > 0 && (
        <Badge variant="secondary" className="gap-1 font-normal">
          <Caravan aria-hidden="true" className="h-3 w-3" />
          {site.permittedEquipment.join(", ")}
        </Badge>
      )}
    </div>
  );
}

/** Accessible pagination navigation shared by Cards and Grid views. */
export function CampsitePagination({
  page,
  pageCount,
  totalMatchingSites,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  totalMatchingSites: number;
  onPageChange: (nextPage: number) => void;
}) {
  if (pageCount <= 1) return null;

  const startIndex = page * SITES_PER_PAGE + 1;
  const endIndex = Math.min((page + 1) * SITES_PER_PAGE, totalMatchingSites);

  return (
    <nav
      aria-label="Campsite pages"
      className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-4"
    >
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label="Previous campsites"
        disabled={page === 0}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span className="text-xs text-muted-foreground">
        {startIndex}–{endIndex} of {totalMatchingSites} sites
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label="Next campsites"
        disabled={page >= pageCount - 1}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </nav>
  );
}

export interface CampsiteCardListProps {
  items: FilteredFoundSite[];
  totalMatchingSites: number;
  page: number;
  pageCount: number;
  onPageChange: (nextPage: number) => void;
  isMultiCampground: boolean;
  scanCampgroundName: string | null;
  hasDateSelection: boolean;
  includeYearByDefault: boolean;
}

/** Deduplicated campsite cards showing capabilities, qualifying stays, and booking actions. */
export function CampsiteCardList({
  items,
  totalMatchingSites,
  page,
  pageCount,
  onPageChange,
  isMultiCampground,
  scanCampgroundName,
  hasDateSelection,
  includeYearByDefault,
}: CampsiteCardListProps) {
  const [expandedSites, setExpandedSites] = useState<ReadonlySet<string>>(
    () => new Set(),
  );

  const toggleExpanded = (siteKey: string) => {
    setExpandedSites((previous) => {
      const next = new Set(previous);
      if (next.has(siteKey)) next.delete(siteKey);
      else next.add(siteKey);
      return next;
    });
  };

  return (
    <div>
      <ul className="space-y-3">
        {items.map(({ site, matchingStayKeys }) => {
          const showCampground = Boolean(
            site.campgroundName &&
            (isMultiCampground ||
              !scanCampgroundName ||
              site.campgroundName.toLowerCase() !==
                scanCampgroundName.toLowerCase()),
          );

          // Order matching stays first when a date filter is active, preserving chronological order within each group.
          const orderedStays = hasDateSelection
            ? [
                ...site.stays.filter((s) => matchingStayKeys.has(stayKey(s))),
                ...site.stays.filter((s) => !matchingStayKeys.has(stayKey(s))),
              ]
            : site.stays;

          const isExpanded = expandedSites.has(site.key);
          const visibleStays = isExpanded
            ? orderedStays
            : orderedStays.slice(0, MAX_INITIAL_STAYS);
          const hiddenCount = orderedStays.length - visibleStays.length;

          return (
            <li
              key={site.key}
              className="rounded-lg border bg-card p-4 transition-colors hover:border-border/80"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1.5">
                  {showCampground && (
                    <p className="text-xs font-medium text-muted-foreground">
                      {site.campgroundName}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="break-words text-base font-semibold leading-snug">
                      {site.displayName}
                    </h3>
                    {site.isStale && (
                      <Badge
                        variant="warning"
                        className="gap-1 text-[11px]"
                        title={
                          site.lastCheckedAt
                            ? `Last checked ${formatRelativeTime(site.lastCheckedAt)}`
                            : "Retained from last successful check"
                        }
                      >
                        <AlertTriangle aria-hidden="true" className="h-3 w-3" />
                        Stale
                        {site.lastCheckedAt
                          ? ` · ${formatRelativeTime(site.lastCheckedAt)}`
                          : ""}
                      </Badge>
                    )}
                  </div>
                  <SiteCapabilities site={site} />
                </div>

                {site.bookingUrl && (
                  <Button
                    asChild
                    variant="outline"
                    size="sm"
                    className="w-full shrink-0 gap-1.5 sm:w-auto"
                  >
                    <a
                      href={site.bookingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`View ${site.displayName} on provider website${site.campgroundName ? ` (${site.campgroundName})` : ""}`}
                    >
                      View on provider
                      <ExternalLink
                        aria-hidden="true"
                        className="h-3.5 w-3.5"
                      />
                    </a>
                  </Button>
                )}
              </div>

              {/* Qualifying stays */}
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
                {visibleStays.map((stay) => {
                  const key = stayKey(stay);
                  const isMatch = hasDateSelection && matchingStayKeys.has(key);
                  const includeYear =
                    includeYearByDefault ||
                    stay.start.slice(0, 4) !== stay.end.slice(0, 4);

                  return (
                    <span
                      key={key}
                      data-matching={isMatch ? "true" : "false"}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs",
                        isMatch
                          ? "border-primary bg-primary/10 font-medium text-primary"
                          : hasDateSelection
                            ? "border-border/70 bg-muted/30 text-muted-foreground"
                            : "border-border bg-muted/40 text-foreground",
                      )}
                    >
                      <time dateTime={stay.start}>
                        {formatStayDate(stay.start, includeYear)}
                      </time>
                      <span aria-hidden="true" className="opacity-60">
                        →
                      </span>
                      <time dateTime={stay.end}>
                        {formatStayDate(stay.end, includeYear)}
                      </time>
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                          isMatch
                            ? "bg-primary/15 text-primary"
                            : "bg-background text-muted-foreground",
                        )}
                      >
                        {stay.nights} night{stay.nights !== 1 ? "s" : ""}
                      </span>
                    </span>
                  );
                })}

                {orderedStays.length > MAX_INITIAL_STAYS && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs text-primary"
                    onClick={() => toggleExpanded(site.key)}
                  >
                    {isExpanded ? (
                      <>
                        Show fewer stays
                        <ChevronUp
                          aria-hidden="true"
                          className="ml-1 h-3 w-3"
                        />
                      </>
                    ) : (
                      <>
                        +{hiddenCount} more stay{hiddenCount !== 1 ? "s" : ""}
                        <ChevronDown
                          aria-hidden="true"
                          className="ml-1 h-3 w-3"
                        />
                      </>
                    )}
                  </Button>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <CampsitePagination
        page={page}
        pageCount={pageCount}
        totalMatchingSites={totalMatchingSites}
        onPageChange={onPageChange}
      />
    </div>
  );
}
