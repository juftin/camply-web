import { useState, useMemo, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Search,
  Filter,
  MapPin,
  Tent,
  Mountain,
  Zap,
  SlidersHorizontal,
  RotateCcw,
  Bell,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Loader2,
} from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ScanForm } from "@/components/ScanForm";
import { useSearchExplore } from "@/hooks/useSearch";
import { toTitleCase } from "@/lib/utils";
import type { Campground, SearchResult } from "@/lib/structs";

const POPULAR_STATES = ["CA", "CO", "WA", "OR", "UT", "AZ", "TX", "FL"];

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Extract search parameters from URL
  const query = searchParams.get("q") || "";
  const state = searchParams.get("state") || "";
  const hasElectric = searchParams.get("electric") === "true";
  const petsAllowed = searchParams.get("pets") === "true";
  const minRvLength = searchParams.get("rv")
    ? parseInt(searchParams.get("rv")!, 10)
    : 0;
  const sortBy = searchParams.get("sort") || "relevance";
  const parsedPage = Number(searchParams.get("page") || "1");
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  // Local state for free-text search input
  const [searchInput, setSearchInput] = useState(query);
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  // Build API exploration parameters
  const exploreParams = useMemo(
    () => ({
      query: query || undefined,
      state: state || undefined,
      hasElectric: hasElectric || undefined,
      petsAllowed: petsAllowed || undefined,
      minRvLength: minRvLength > 0 ? minRvLength : undefined,
      sortBy,
      page,
      pageSize: 20,
    }),
    [query, state, hasElectric, petsAllowed, minRvLength, sortBy, page],
  );

  const { data, isLoading, isFetching, isPlaceholderData, error, refetch } =
    useSearchExplore(exploreParams);

  useEffect(() => {
    setSearchInput(query);
  }, [query]);

  useEffect(() => {
    if (searchInput.trim() === query) return;
    const timeout = window.setTimeout(() => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (searchInput.trim()) next.set("q", searchInput.trim());
          else next.delete("q");
          next.delete("page");
          return next;
        },
        { replace: true },
      );
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [searchInput, query, setSearchParams]);

  // Filters commit the current input immediately, including pending typing.
  const updateParams = (updates: Record<string, string | null>) => {
    setSearchParams((current) => {
      const nextParams = new URLSearchParams(current);
      if (!("page" in updates)) {
        nextParams.delete("page");
        if (searchInput.trim()) nextParams.set("q", searchInput.trim());
        else nextParams.delete("q");
      }
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === "" || value === "0") {
          nextParams.delete(key);
        } else {
          nextParams.set(key, value);
        }
      }
      return nextParams;
    });
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateParams({ q: searchInput.trim() || null });
  };

  const handleClearFilters = () => {
    setSearchInput("");
    setSearchParams(new URLSearchParams());
  };

  const activeFilterCount =
    (state ? 1 : 0) +
    (hasElectric ? 1 : 0) +
    (petsAllowed ? 1 : 0) +
    (minRvLength > 0 ? 1 : 0) +
    (sortBy !== "relevance" ? 1 : 0);

  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;
  const items = data?.items || [];
  const facets = data?.facets;

  // Convert SearchResult to Campground structure for prefilling ScanForm
  const toCampgroundModel = (item: SearchResult): Campground => ({
    id: item.campground_id || item.id,
    provider_id: item.provider_id,
    recreation_area_id: item.recreation_area_id,
    name: item.campground_name || item.recreation_area_name || "Campground",
    description: null,
    country: item.country || null,
    state: item.state || null,
    longitude: item.longitude || null,
    latitude: item.latitude || null,
    reservable: item.reservable ?? true,
    enabled: true,
    url: "",
  });

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Discover Campgrounds
        </h1>
        <p className="text-muted-foreground">
          Explore reservable campsites across National and State Parks. Filter
          by amenities, RV length, and location.
        </p>
      </div>

      {/* Search Bar & Mobile Filter Trigger */}
      <div className="mb-8 flex gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              type="search"
              aria-label="Search campgrounds"
              placeholder="Search by campground name, park, or city..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-11 h-12 text-base"
            />
          </div>
          <Button type="submit" size="lg" className="h-12 px-6">
            Search
          </Button>
        </form>

        <Button
          variant="outline"
          size="lg"
          onClick={() => setIsFilterOpen(!isFilterOpen)}
          className="md:hidden h-12 flex items-center gap-2"
        >
          <SlidersHorizontal className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0.2">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Filters Sidebar */}
        <aside
          className={`space-y-6 md:block ${isFilterOpen ? "block" : "hidden"}`}
        >
          <div className="p-5 border rounded-lg bg-card shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-3 border-b">
              <div className="flex items-center gap-2 font-semibold">
                <Filter className="h-4 w-4 text-primary" />
                <span>Filters</span>
                {activeFilterCount > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {activeFilterCount} active
                  </Badge>
                )}
              </div>
              {activeFilterCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearFilters}
                  className="h-8 text-xs text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Reset
                </Button>
              )}
            </div>

            {/* State Filter */}
            <div>
              <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider mb-2 block">
                Popular States
              </Label>
              <div className="flex flex-wrap gap-1.5">
                {POPULAR_STATES.map((st) => {
                  const isSelected = state.toUpperCase() === st;
                  const count = facets?.states?.[st];
                  return (
                    <button
                      key={st}
                      type="button"
                      onClick={() =>
                        updateParams({ state: isSelected ? null : st })
                      }
                      className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                        isSelected
                          ? "bg-primary text-primary-foreground border-primary font-medium"
                          : "bg-muted/40 hover:bg-muted text-foreground border-border"
                      }`}
                    >
                      {st} {count ? `(${count})` : ""}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Amenities Section */}
            <div className="space-y-4 pt-2 border-t">
              <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider block">
                Amenities & Features
              </Label>

              <div className="flex items-center justify-between">
                <Label
                  htmlFor="electric-toggle"
                  className="cursor-pointer text-sm font-normal"
                >
                  Electric Hookups
                </Label>
                <Switch
                  id="electric-toggle"
                  checked={hasElectric}
                  onCheckedChange={(checked) =>
                    updateParams({ electric: checked ? "true" : null })
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <Label
                  htmlFor="pets-toggle"
                  className="cursor-pointer text-sm font-normal"
                >
                  Pets Allowed
                </Label>
                <Switch
                  id="pets-toggle"
                  checked={petsAllowed}
                  onCheckedChange={(checked) =>
                    updateParams({ pets: checked ? "true" : null })
                  }
                />
              </div>
            </div>

            {/* RV Length Filter */}
            <div className="space-y-3 pt-2 border-t">
              <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider block">
                Minimum RV Length
              </Label>
              <div className="grid grid-cols-4 gap-1.5">
                {[
                  { label: "Any", val: 0 },
                  { label: "25'", val: 25 },
                  { label: "30'", val: 30 },
                  { label: "35'+", val: 35 },
                ].map((opt) => (
                  <button
                    key={opt.val}
                    type="button"
                    onClick={() =>
                      updateParams({
                        rv: opt.val === minRvLength ? null : String(opt.val),
                      })
                    }
                    className={`text-xs py-1.5 rounded border text-center transition-colors ${
                      minRvLength === opt.val
                        ? "bg-primary text-primary-foreground border-primary font-medium"
                        : "bg-muted/40 hover:bg-muted border-border"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Sort Order */}
            <div className="space-y-2 pt-2 border-t">
              <Label className="text-xs font-semibold uppercase text-muted-foreground tracking-wider block">
                Sort By
              </Label>
              <select
                value={sortBy}
                onChange={(e) => updateParams({ sort: e.target.value })}
                className="w-full text-sm border rounded-md p-2 bg-background text-foreground border-border"
              >
                <option value="relevance">Relevance</option>
                <option value="name_asc">Name (A-Z)</option>
                <option value="name_desc">Name (Z-A)</option>
              </select>
            </div>
          </div>
        </aside>

        {/* Results Section */}
        <main className="md:col-span-3 space-y-6" aria-busy={isFetching}>
          {/* Results Summary Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b">
            <div>
              <p
                className="text-sm font-medium"
                role="status"
                aria-live="polite"
              >
                {isLoading || isPlaceholderData ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Searching campgrounds...
                  </span>
                ) : (
                  <>
                    Found{" "}
                    <span className="font-bold text-foreground">
                      {total}
                    </span>{" "}
                    {total === 1 ? "campground" : "campgrounds"}
                    {query && <span> for "{query}"</span>}
                    {state && <span> in {state.toUpperCase()}</span>}
                  </>
                )}
              </p>
            </div>

            {isFetching && !isLoading && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Updating...
              </span>
            )}
          </div>

          {/* Results List */}
          {error ? (
            <Card>
              <CardContent className="p-8 text-center text-red-600">
                Failed to load campgrounds. Please try again or adjust your
                filters.
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => void refetch()}
                >
                  Retry
                </Button>
              </CardContent>
            </Card>
          ) : !isLoading && items.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center space-y-4">
                <Tent className="h-12 w-12 mx-auto text-muted-foreground/60" />
                <div>
                  <h3 className="text-lg font-semibold">
                    No campgrounds found
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">
                    We couldn't find any campsites matching your filters. Try
                    loosening amenity constraints or searching a broader area.
                  </p>
                </div>
                {activeFilterCount > 0 && (
                  <Button variant="outline" onClick={handleClearFilters}>
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Clear All Filters
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {items.map((item) => {
                const displayName =
                  item.campground_name ||
                  item.recreation_area_name ||
                  "Campground";
                const parentArea =
                  item.entity_type === "Campground"
                    ? item.recreation_area_name
                    : null;
                const isCampground = item.entity_type === "Campground";
                const detailUrl =
                  isCampground && item.campground_id
                    ? `/campground/${item.provider_id}/${item.campground_id}`
                    : `/rec-area/${item.provider_id}/${item.recreation_area_id}`;

                return (
                  <Card
                    key={item.id}
                    className="overflow-hidden hover:border-primary/40 transition-colors"
                  >
                    <CardContent className="p-5">
                      <div className="flex flex-col sm:flex-row justify-between gap-4">
                        <div className="space-y-1.5 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                              {isCampground ? (
                                <Tent className="h-3 w-3" />
                              ) : (
                                <Mountain className="h-3 w-3" />
                              )}
                              {isCampground ? "Campground" : "Recreation Area"}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {toTitleCase(item.provider_name)}
                            </Badge>
                            {item.state && (
                              <Badge variant="secondary" className="text-xs">
                                {item.state.toUpperCase()}
                              </Badge>
                            )}
                          </div>

                          <h3 className="text-lg font-bold text-foreground">
                            <Link
                              to={detailUrl}
                              className="hover:text-primary transition-colors"
                            >
                              {toTitleCase(displayName)}
                            </Link>
                          </h3>

                          {parentArea && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              in {toTitleCase(parentArea)}
                              {item.city ? ` · ${toTitleCase(item.city)}` : ""}
                            </p>
                          )}

                          {/* Amenity Pills */}
                          <div className="flex flex-wrap gap-2 pt-2">
                            {item.has_electric && (
                              <span className="inline-flex items-center gap-1 text-xs bg-amber-500/10 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded">
                                <Zap className="h-3 w-3" />
                                Electric
                              </span>
                            )}
                            {item.pets_allowed && (
                              <span className="inline-flex items-center gap-1 text-xs bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded">
                                🐾 Pets
                              </span>
                            )}
                            {item.max_rv_length && item.max_rv_length > 0 ? (
                              <span className="inline-flex items-center gap-1 text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded">
                                🚐 RV {item.max_rv_length}'
                              </span>
                            ) : null}
                          </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex sm:flex-col justify-end sm:justify-center gap-2 shrink-0">
                          {isCampground && (
                            <ScanForm
                              preselectedCampground={toCampgroundModel(item)}
                              preselectedProviderId={item.provider_id}
                              trigger={
                                <Button size="sm" className="gap-1.5">
                                  <Bell className="h-3.5 w-3.5" />
                                  Monitor
                                </Button>
                              }
                            />
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                            className="gap-1.5"
                          >
                            <Link to={detailUrl}>
                              Details
                              <ExternalLink className="h-3 w-3" />
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          {!error && totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-6">
              <Button
                variant="outline"
                size="sm"
                disabled={isFetching || isPlaceholderData || page <= 1}
                onClick={() => updateParams({ page: String(page - 1) })}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground px-3">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={isFetching || isPlaceholderData || page >= totalPages}
                onClick={() => updateParams({ page: String(page + 1) })}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
