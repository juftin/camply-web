import { useQuery } from "@tanstack/react-query";
import {
  searchCampgrounds,
  searchExplore,
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
