import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  locateByIp,
  searchCampgrounds,
  searchExplore,
  mapQueryParams,
  searchMap,
  searchMapSummary,
  searchMapMembers,
  type SearchExploreParams,
} from "@/lib/api";
import { SearchResult, SearchExploreResponse } from "@/lib/structs.ts";

export function useSearch(query: string, enabled: boolean = true) {
  const trimmedQuery = query.trim();
  const shouldSearch = enabled && trimmedQuery.length >= 2;

  return useQuery<SearchResult[]>({
    queryKey: ["search", trimmedQuery],
    queryFn: ({ signal }) => searchCampgrounds(trimmedQuery, 20, signal),
    enabled: shouldSearch,
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep cache for 10 minutes
    refetchOnWindowFocus: false,
    retry: 1,
    // Keep previous data while loading new results to prevent flicker
    placeholderData: (previousData) => previousData,
  });
}

export function useSearchExplore(
  params: SearchExploreParams = {},
  enabled: boolean = true,
) {
  return useQuery<SearchExploreResponse>({
    queryKey: ["search-explore", params],
    queryFn: ({ signal }) => searchExplore(params, signal),
    enabled,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    placeholderData: (previousData) => previousData,
  });
}

export function useMapSummary(params: SearchExploreParams) {
  return useQuery({
    queryKey: ["map-summary", mapQueryParams(params)],
    queryFn: ({ signal }) => searchMapSummary(params, signal),
    staleTime: 120000,
    retry: 1,
  });
}
export function useMapFeatures(
  params: SearchExploreParams,
  viewport: { bounds: import("@/lib/maps").GeoBounds; zoom: number } | null,
) {
  return useQuery({
    queryKey: ["map-features", mapQueryParams(params), viewport],
    queryFn: ({ signal }) =>
      searchMap(params, viewport!.bounds, viewport!.zoom, signal),
    enabled: viewport !== null,
    staleTime: 120000,
    retry: 1,
    placeholderData: (previous) => previous,
  });
}
export function useMapMembers(
  params: SearchExploreParams,
  selection: { bounds: import("@/lib/maps").GeoBounds; cellId: string } | null,
) {
  return useInfiniteQuery({
    queryKey: ["map-members", mapQueryParams(params), selection],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ signal, pageParam }) =>
      searchMapMembers(
        params,
        selection!.bounds,
        selection!.cellId,
        pageParam,
        signal,
      ),
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    enabled: selection !== null,
    staleTime: 120000,
    retry: 1,
  });
}

/** Cache an approximate IP location for this visit and gracefully fall back. */
export function useIpLocation(enabled: boolean) {
  return useQuery({
    queryKey: ["ip-location"],
    queryFn: ({ signal }) => locateByIp(signal),
    enabled,
    staleTime: Infinity,
    retry: false,
    refetchOnWindowFocus: false,
  });
}
