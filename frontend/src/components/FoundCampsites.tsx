import { useEffect, useRef, useState } from "react";
import { Calendar, ExternalLink, Search, Tent, Zap } from "lucide-react";
import { useLocation } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ScanDetailResponse } from "@/lib/structs";
import { addDays, formatDisplayDate, formatRelativeTime } from "@/lib/utils";

/** Turn available nights into distinct check-in/check-out blocks. */
function availableStays(dates: string[]) {
  const blocks: { start: string; end: string; nights: number }[] = [];
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

export const FoundCampsites = ({ scan }: { scan: ScanDetailResponse }) => {
  const [query, setQuery] = useState("");
  const section = useRef<HTMLElement>(null);
  const { hash } = useLocation();
  useEffect(() => {
    if (hash === "#results")
      section.current?.scrollIntoView?.({ block: "start" });
  }, [hash]);
  const results = scan.results ?? [];
  const visible = results.filter((site) =>
    `${site.campsite_name} ${site.campsite_id} ${site.campsite_type ?? ""}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );

  return (
    <section
      id="results"
      ref={section}
      aria-labelledby="found-campsites-heading"
      className="scroll-mt-24"
    >
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle id="found-campsites-heading">Found campsites</CardTitle>
            <Badge variant={results.length ? "success" : "secondary"}>
              {results.length} matching site{results.length !== 1 ? "s" : ""}
            </Badge>
          </div>
          <CardDescription>
            {scan.last_checked_at
              ? `Last checked ${formatRelativeTime(scan.last_checked_at)}.`
              : "Your scan is ready to check for openings."}{" "}
            Availability can change. Confirm your dates with the booking
            provider.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center">
              <Tent className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
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
              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative sm:max-w-xs w-full">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    aria-label="Search found campsites"
                    placeholder="Search sites"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    className="pl-9"
                  />
                </div>
                <p
                  role="status"
                  className="text-sm text-muted-foreground whitespace-nowrap"
                >
                  {visible.length} of {results.length} campsites
                </p>
              </div>
              <p className="mb-3 text-xs text-muted-foreground">
                Available stays · Check-in – check-out
              </p>
              <ul className="space-y-3">
                {visible.map((site) => {
                  const name =
                    site.campsite_name || `Campsite ${site.campsite_id}`;
                  const stays = availableStays(site.available_dates).filter(
                    (stay) => stay.nights >= scan.min_stay_length,
                  );
                  return (
                    <li
                      key={site.campsite_id}
                      className="rounded-lg border p-4"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <h3 className="font-semibold break-words">{name}</h3>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {site.campsite_type && (
                              <Badge variant="secondary">
                                {site.campsite_type}
                              </Badge>
                            )}
                            {site.is_electric && (
                              <Badge variant="outline" className="gap-1">
                                <Zap className="h-3 w-3" />
                                Electric hookup
                              </Badge>
                            )}
                            {site.is_accessible && (
                              <Badge variant="outline">Accessible</Badge>
                            )}
                          </div>
                        </div>
                        {site.booking_url && (
                          <Button asChild size="sm" className="shrink-0">
                            <a
                              href={site.booking_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              aria-label={`Book ${name} on provider website`}
                            >
                              View booking options
                              <ExternalLink className="ml-2 h-3.5 w-3.5" />
                            </a>
                          </Button>
                        )}
                      </div>
                      <ul className="mt-4 space-y-2">
                        {stays.map((stay) => (
                          <li
                            key={stay.start}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
                          >
                            <Calendar className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span>
                              {formatDisplayDate(stay.start, false)} –{" "}
                              {formatDisplayDate(stay.end, false)}
                            </span>
                            <span className="text-muted-foreground">
                              {stay.nights} night{stay.nights !== 1 ? "s" : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </li>
                  );
                })}
              </ul>
              {visible.length === 0 && (
                <div className="py-8 text-center">
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
        </CardContent>
      </Card>
    </section>
  );
};
