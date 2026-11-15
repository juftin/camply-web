import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminOverview,
  listAdminUsers,
  getAdminUser,
  createAdminUser,
  updateAdminUser,
  listAdminAccessRequests,
  updateAdminAccessRequest,
  listAdminScans,
  getAdminScan,
  updateAdminScan,
  getAdminTarget,
  listAdminAudit,
  getAdminOperations,
  listAdminOperationsTasks,
  getAdminOperationsTask,
  syncAdminProviders,
  getAdminTrends,
  shouldRetryProtectedQuery,
} from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type {
  AdminOverviewResponse,
  AdminUserCreateRequest,
  AdminUserListResponse,
  AdminUserDetailResponse,
  AdminUserUpdateRequest,
  AdminAccessRequestListResponse,
  AdminAccessRequestUpdateRequest,
  AdminScanListResponse,
  AdminScanDetailResponse,
  AdminScanUpdateRequest,
  AdminTargetDetailResponse,
  AdminAuditListResponse,
  AdminOperationsResponse,
  AdminOperationsTasksResponse,
  AdminOperationsTaskDetail,
  AdminTrendsResponse,
} from "@/lib/structs";

function useAdminAuthEnabled(): boolean {
  const { isReady, user } = useAuth();
  return isReady && Boolean(user?.is_admin);
}

export function useAdminOverview() {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminOverviewResponse>({
    queryKey: ["admin", "overview"],
    queryFn: getAdminOverview,
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
    refetchInterval: 15000,
  });
}

export function useAdminUsers(params?: {
  search?: string;
  scanning_enabled?: boolean;
  limit?: number;
  offset?: number;
}) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminUserListResponse>({
    queryKey: ["admin", "users", params],
    queryFn: () => listAdminUsers(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
  });
}

export function useAdminUser(userId: string) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminUserDetailResponse>({
    queryKey: ["admin", "users", userId],
    queryFn: () => getAdminUser(userId),
    enabled: authEnabled && Boolean(userId),
    retry: shouldRetryProtectedQuery,
  });
}

export function useCreateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminUserCreateRequest) => createAdminUser(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      payload,
    }: {
      userId: string;
      payload: AdminUserUpdateRequest;
    }) => updateAdminUser(userId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "access-requests"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "targets"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

export function useAdminAccessRequests(params?: {
  status?: "pending" | "approved" | "rejected";
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminAccessRequestListResponse>({
    queryKey: ["admin", "access-requests", params],
    queryFn: () => listAdminAccessRequests(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
  });
}

export function useUpdateAdminAccessRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      requestId,
      payload,
    }: {
      requestId: string;
      payload: AdminAccessRequestUpdateRequest;
    }) => updateAdminAccessRequest(requestId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "access-requests"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useAdminScans(params?: {
  owner_id?: string;
  is_active?: boolean;
  is_eligible?: boolean;
  provider_id?: number;
  target_status?: "active" | "overdue" | "dormant";
  limit?: number;
  offset?: number;
}) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminScanListResponse>({
    queryKey: ["admin", "scans", params],
    queryFn: () => listAdminScans(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
  });
}

export function useAdminScan(scanId: string) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminScanDetailResponse>({
    queryKey: ["admin", "scans", scanId],
    queryFn: () => getAdminScan(scanId),
    enabled: authEnabled && Boolean(scanId),
    retry: shouldRetryProtectedQuery,
  });
}

export function useUpdateAdminScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      scanId,
      payload,
    }: {
      scanId: string;
      payload: AdminScanUpdateRequest;
    }) => updateAdminScan(scanId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "targets"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

export function useAdminTarget(
  targetId: string,
  params?: { limit?: number; offset?: number },
) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminTargetDetailResponse>({
    queryKey: ["admin", "targets", targetId, params],
    queryFn: () => getAdminTarget(targetId, params),
    enabled: authEnabled && Boolean(targetId),
    retry: shouldRetryProtectedQuery,
  });
}

export function useAdminAudit(params?: { limit?: number; offset?: number }) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminAuditListResponse>({
    queryKey: ["admin", "audit", params],
    queryFn: () => listAdminAudit(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
  });
}

export function useAdminOperations() {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminOperationsResponse>({
    retry: false,
    queryKey: ["admin", "operations"],
    queryFn: getAdminOperations,
    enabled: authEnabled,
    refetchInterval: 15000,
  });
}

export function useAdminOperationsTasks(params?: {
  limit?: number;
  offset?: number;
  task_name?: string;
  outcome?: string;
  provider?: string;
  search?: string;
}) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminOperationsTasksResponse>({
    queryKey: ["admin", "operations", "tasks", params],
    queryFn: () => listAdminOperationsTasks(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
    refetchInterval: 15000,
  });
}

export function useAdminOperationsTask(taskId: string) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminOperationsTaskDetail>({
    queryKey: ["admin", "operations", "tasks", taskId],
    queryFn: () => getAdminOperationsTask(taskId),
    enabled: authEnabled && Boolean(taskId),
    retry: shouldRetryProtectedQuery,
  });
}

export function useSyncAdminProviders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncAdminProviders,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "operations"] });
      queryClient.invalidateQueries({
        queryKey: ["admin", "operations", "tasks"],
      });
    },
  });
}

export function useAdminTrends(params?: {
  group?: "usage" | "api" | "worker" | "provider";
  range?: "24h" | "7d" | "30d";
  endpoint?: string;
  task_name?: string;
  provider?: string;
}) {
  const authEnabled = useAdminAuthEnabled();
  return useQuery<AdminTrendsResponse>({
    queryKey: ["admin", "trends", params],
    queryFn: () => getAdminTrends(params),
    enabled: authEnabled,
    retry: shouldRetryProtectedQuery,
    refetchInterval: 30000,
  });
}
