import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listScans,
  createScan,
  getScan,
  updateScan,
  deleteScan,
  getApiErrorMessage,
  shouldRetryProtectedQuery,
} from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type {
  ScanCreateRequest,
  ScanUpdateRequest,
  ScanResponse,
  ScanDetailResponse,
  ScanListResponse,
} from "@/lib/structs";

// ---------------------------------------------------------------------------
// List scans
// ---------------------------------------------------------------------------

export function useScans(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}) {
  const { isReady, user } = useAuth();
  return useQuery<ScanListResponse>({
    queryKey: ["scans", "list", params],
    queryFn: () => listScans(params),
    enabled: isReady && Boolean(user),
    retry: shouldRetryProtectedQuery,
    staleTime: 30 * 1000, // 30 seconds – scans update frequently
    refetchInterval: 30 * 1000,
  });
}

// ---------------------------------------------------------------------------
// Single scan detail
// ---------------------------------------------------------------------------

export function useScanDetail(scanId: string | null) {
  const { isReady, user } = useAuth();
  return useQuery<ScanDetailResponse>({
    queryKey: ["scans", "detail", scanId],
    queryFn: () => getScan(scanId!),
    retry: shouldRetryProtectedQuery,
    enabled: scanId !== null && isReady && Boolean(user),
    staleTime: 15 * 1000,
    refetchInterval: 15 * 1000,
  });
}

// ---------------------------------------------------------------------------
// Create scan
// ---------------------------------------------------------------------------

export function useCreateScan() {
  const queryClient = useQueryClient();

  return useMutation<ScanResponse, Error, ScanCreateRequest>({
    mutationFn: (payload) => createScan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Update scan
// ---------------------------------------------------------------------------

export function useUpdateScan() {
  const queryClient = useQueryClient();

  return useMutation<
    ScanResponse,
    Error,
    { scanId: string; payload: ScanUpdateRequest }
  >({
    mutationFn: ({ scanId, payload }) => updateScan(scanId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["scans"] }),
  });
}

// ---------------------------------------------------------------------------
// Delete scan
// ---------------------------------------------------------------------------

export function useDeleteScan() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (scanId) => deleteScan(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}

export { getApiErrorMessage };
