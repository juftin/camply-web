import { useQuery } from "@tanstack/react-query";
import { listProviders } from "@/lib/api";
import type { Provider, ProviderFilterCapabilities } from "@/lib/structs";

export const DEFAULT_PROVIDER_FILTER_CAPABILITIES: ProviderFilterCapabilities =
  {
    preferred_types: true,
    require_electric: true,
    require_accessible: true,
    min_rv_length: true,
  };

/** Load and cache providers along with their supported monitor filter capabilities. */
export function useProviders(enabled: boolean = true) {
  return useQuery<Provider[]>({
    queryKey: ["providers"],
    queryFn: listProviders,
    enabled,
    staleTime: 30 * 60 * 1000,
  });
}
