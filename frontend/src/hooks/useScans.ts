import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listScans,
  createScan,
  getScan,
  updateScan,
  deleteScan,
  getApiErrorMessage,
} from "@/lib/api";
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
  return useQuery<ScanListResponse>({
    queryKey: ["scans", "list", params],
    queryFn: () => listScans(params),
    staleTime: 30 * 1000, // 30 seconds – scans update frequently
  });
}

// ---------------------------------------------------------------------------
// Single scan detail
// ---------------------------------------------------------------------------

export function useScanDetail(scanId: string | null) {
  return useQuery<ScanDetailResponse>({
    queryKey: ["scans", "detail", scanId],
    queryFn: () => getScan(scanId!),
    enabled: scanId !== null,
    staleTime: 15 * 1000,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
    },
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
