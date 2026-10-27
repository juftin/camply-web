import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  Search,
  Tent,
  Zap,
} from "lucide-react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ScanDetailResponse, ScanResultItem } from "@/lib/structs";
import {
  addDays,
  formatDisplayDate,
  formatRelativeTime,
  parseIsoDate,
} from "@/lib/utils";

/** A maximal consecutive opening, with an exclusive check-out date. */
interface AvailableStay {
  start: string;
  end: string;
  nights: number;
}

/** Turn available nights into distinct check-in/check-out blocks. */
function availableStays(dates: string[]): AvailableStay[] {
  const blocks: AvailableStay[] = [];
  for (const date of [...new Set(dates)].sort()) {
    const previous = blocks[blocks.length - 1];
    if (previous?.end === date) {
      previous.end = addDays(date, 1);
      previous.nights += 1;
    } else {
      blocks.push({ start: date, end: addDays(date, 1), nights: 1 });
    }
  }
  return blocks;
}

/** Use compact weekdays; include years when a stay crosses New Year's Day. */
function stayDate(date: string, includeYear: boolean): string {
  return parseIsoDate(date).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    ...(includeYear ? { year: "numeric" } : {}),
  });
}

/** Browse matching campsites under their shared check-in/check-out ranges. */
export const FoundCampsites = ({ scan }: { scan: ScanDetailResponse }) => {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("soonest");
  const section = useRef<HTMLElement>(null);
  const { hash } = useLocation();
  useEffect(() => {
    if (hash === "#results")
      section.current?.scrollIntoView?.({ block: "start" });
  }, [hash]);

  const groups = new Map<string, AvailableStay & { sites: ScanResultItem[] }>();
  for (const site of scan.results ?? []) {
    for (const stay of availableStays(site.available_dates)) {
      if (stay.nights < scan.min_stay_length) continue;
      const key = `${stay.start}/${stay.end}`;
      const group = groups.get(key);
      if (group) group.sites.push(site);
      else groups.set(key, { ...stay, sites: [site] });
    }
  }
  const normalizedQuery = query.trim().toLowerCase();
  const visible = [...groups.values()]
    .map((group) => ({
      ...group,
      sites: group.sites.filter((site) =>
        `${site.campsite_name} ${site.campsite_id} ${site.campsite_type ?? ""}`
          .toLowerCase()
          .includes(normalizedQuery),
      ),
    }))
    .filter((group) => group.sites.length > 0)
    .sort(
      (a, b) =>
        (sort === "longest" ? b.nights - a.nights : 0) ||
        a.start.localeCompare(b.start) ||
        a.end.localeCompare(b.end),
    );
  const siteCount = new Set(
    visible.flatMap((group) => group.sites.map((site) => site.campsite_id)),
  ).size;

  return (
    <section
      id="results"
      ref={section}
      aria-labelledby="found-campsites-heading"
      className="scroll-mt-24"
    >
      <Card className="overflow-hidden">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle id="found-campsites-heading">Found campsites</CardTitle>
            <p role="status" className="text-sm text-muted-foreground">
              {siteCount} site{siteCount !== 1 ? "s" : ""} · {visible.length}{" "}
              date range{visible.length !== 1 ? "s" : ""}
            </p>
          </div>
          <CardDescription className="flex items-center gap-1.5">
            <Clock aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
            {scan.last_checked_at
              ? `Last checked ${formatRelativeTime(scan.last_checked_at)}`
              : "Your scan is ready to check for openings."}
          </CardDescription>
          {groups.size > 0 && (
            <div className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:max-w-xs">
                <Search
                  aria-hidden="true"
                  className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                />
                <Input
                  type="search"
                  aria-label="Search found campsites"
                  placeholder="Search sites or campsite types"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="pl-9"
                />
              </div>
              <label className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                Sort by
                <span className="relative">
                  <select
                    aria-label="Sort date groups"
                    value={sort}
                    onChange={(event) => setSort(event.target.value)}
                    className="h-10 w-44 appearance-none rounded-md border bg-background pl-3 pr-9 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <option value="soonest">Soonest check-in</option>
                    <option value="longest">Longest stay</option>
                  </select>
                  <ChevronDown
                    aria-hidden="true"
                    className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground"
                  />
                </span>
              </label>
            </div>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {groups.size === 0 ? (
            <div className="mx-6 mb-6 rounded-lg border border-dashed p-8 text-center">
              <Tent
                aria-hidden="true"
                className="mx-auto mb-3 h-8 w-8 text-muted-foreground"
              />
              <p className="font-medium">
                {scan.last_checked_at
                  ? "No matching campsites right now"
                  : "Waiting for the first check"}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {scan.is_active
                  ? "Camply will notify you when new openings match your scan."
                  : "This scan is paused. Resume it from your dashboard to check for new openings."}
              </p>
            </div>
          ) : (
            <>
              {visible.map((group, index) => {
                const includeYear =
                  group.start.slice(0, 4) !== group.end.slice(0, 4);
                return (
                  <details
                    key={`${group.start}/${group.end}`}
                    open={normalizedQuery !== "" || index < 2}
                    aria-label={`${formatDisplayDate(group.start, false)} – ${formatDisplayDate(group.end, false)}`}
                    className="group border-t"
                  >
                    <summary className="flex cursor-pointer list-none items-start gap-2 bg-muted/40 px-4 py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:items-center sm:gap-3 sm:px-6 [&::-webkit-details-marker]:hidden">
                      <ChevronRight
                        aria-hidden="true"
                        className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform group-open:rotate-90 sm:mt-0"
                      />
                      <div className="grid min-w-0 grid-cols-[auto_auto_auto] items-start gap-x-1.5 text-xs sm:gap-x-2 sm:text-sm">
                        <div>
                          <time
                            dateTime={group.start}
                            className="font-semibold"
                          >
                            {stayDate(group.start, includeYear)}
                          </time>
                          <p className="mt-1 text-[10px] text-muted-foreground sm:text-xs">
                            Check-in
                          </p>
                        </div>
                        <span
                          aria-hidden="true"
                          className="text-muted-foreground"
                        >
                          →
                        </span>
                        <div>
                          <time dateTime={group.end} className="font-semibold">
                            {stayDate(group.end, includeYear)}
                          </time>
                          <p className="mt-1 text-[10px] text-muted-foreground sm:text-xs">
                            Check-out
                          </p>
                        </div>
                      </div>
                      <div className="ml-auto flex shrink-0 flex-col items-end gap-1 sm:flex-row sm:items-center sm:gap-3">
                        <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                          {group.nights} night{group.nights !== 1 ? "s" : ""}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {group.sites.length} site
                          {group.sites.length !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </summary>
                    <ul className="divide-y pl-9 pr-4 sm:pl-12 sm:pr-6">
                      {group.sites.map((site) => {
                        const name =
                          site.campsite_name || `Campsite ${site.campsite_id}`;
                        return (
                          <li
                            key={site.campsite_id}
                            className="flex items-center justify-between gap-2 py-2"
                          >
                            <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-6">
                              <h3 className="min-w-20 break-words text-sm font-semibold">
                                {name}
                              </h3>
                              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                                {site.campsite_type && (
                                  <span>{site.campsite_type}</span>
                                )}
                                {site.is_electric && (
                                  <span className="inline-flex items-center gap-1">
                                    <Zap
                                      aria-hidden="true"
                                      className="h-3 w-3"
                                    />
                                    Electric hookup
                                  </span>
                                )}
                                {site.is_accessible && <span>Accessible</span>}
                              </div>
                            </div>
                            {site.booking_url && (
                              <a
                                href={site.booking_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label={`View ${name} on provider website`}
                                className="inline-flex min-h-11 shrink-0 items-center gap-1 pl-2 text-xs font-medium text-primary hover:underline"
                              >
                                View on provider
                                <ExternalLink
                                  aria-hidden="true"
                                  className="h-3 w-3"
                                />
                              </a>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </details>
                );
              })}
              {visible.length === 0 && (
                <div className="px-6 py-8 text-center">
                  <p className="text-muted-foreground">
                    No campsites match your search.
                  </p>
                  <Button
                    variant="ghost"
                    onClick={() => setQuery("")}
                    className="mt-2"
                  >
                    Clear search
                  </Button>
                </div>
              )}
            </>
          )}
          <p className="border-t px-6 py-4 text-xs text-muted-foreground">
            Dates show check-in → check-out. Availability can change; confirm
            your dates with the booking provider.
          </p>
        </CardContent>
      </Card>
    </section>
  );
};
