import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAdminOverview,
  listAdminUsers,
  getAdminUser,
  updateAdminUser,
  listAdminScans,
  getAdminScan,
  updateAdminScan,
  getAdminTarget,
  listAdminAudit,
  getAdminOperations,
  listAdminOperationsTasks,
  getAdminOperationsTask,
  getAdminTrends,
} from "@/lib/api";
import type {
  AdminOverviewResponse,
  AdminUserListResponse,
  AdminUserDetailResponse,
  AdminUserUpdateRequest,
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

export function useAdminOverview() {
  return useQuery<AdminOverviewResponse>({
    queryKey: ["admin", "overview"],
    queryFn: getAdminOverview,
    refetchInterval: 15000,
  });
}

export function useAdminUsers(params?: {
  search?: string;
  scanning_enabled?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery<AdminUserListResponse>({
    queryKey: ["admin", "users", params],
    queryFn: () => listAdminUsers(params),
  });
}

export function useAdminUser(userId: string) {
  return useQuery<AdminUserDetailResponse>({
    queryKey: ["admin", "users", userId],
    queryFn: () => getAdminUser(userId),
    enabled: Boolean(userId),
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
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users", userId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

export function useAdminScans(params?: {
  owner_id?: string;
  is_active?: boolean;
  is_eligible?: boolean;
  provider_id?: number;
  limit?: number;
  offset?: number;
}) {
  return useQuery<AdminScanListResponse>({
    queryKey: ["admin", "scans", params],
    queryFn: () => listAdminScans(params),
  });
}

export function useAdminScan(scanId: string) {
  return useQuery<AdminScanDetailResponse>({
    queryKey: ["admin", "scans", scanId],
    queryFn: () => getAdminScan(scanId),
    enabled: Boolean(scanId),
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
    onSuccess: (_, { scanId }) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "scans"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "scans", scanId] });
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
  return useQuery<AdminTargetDetailResponse>({
    queryKey: ["admin", "targets", targetId, params],
    queryFn: () => getAdminTarget(targetId, params),
    enabled: Boolean(targetId),
  });
}

export function useAdminAudit(params?: { limit?: number; offset?: number }) {
  return useQuery<AdminAuditListResponse>({
    queryKey: ["admin", "audit", params],
    queryFn: () => listAdminAudit(params),
  });
}

export function useAdminOperations() {
  return useQuery<AdminOperationsResponse>({
    queryKey: ["admin", "operations"],
    queryFn: getAdminOperations,
    refetchInterval: 15000,
  });
}

export function useAdminOperationsTasks(params?: {
  limit?: number;
  offset?: number;
  task_name?: string;
  outcome?: string;
}) {
  return useQuery<AdminOperationsTasksResponse>({
    queryKey: ["admin", "operations", "tasks", params],
    queryFn: () => listAdminOperationsTasks(params),
    refetchInterval: 15000,
  });
}

export function useAdminOperationsTask(taskId: string) {
  return useQuery<AdminOperationsTaskDetail>({
    queryKey: ["admin", "operations", "tasks", taskId],
    queryFn: () => getAdminOperationsTask(taskId),
    enabled: Boolean(taskId),
  });
}

export function useAdminTrends(params?: {
  group?: "usage" | "api" | "worker" | "provider";
  range?: "24h" | "7d" | "30d";
  endpoint?: string;
  task_name?: string;
  provider?: string;
}) {
  return useQuery<AdminTrendsResponse>({
    queryKey: ["admin", "trends", params],
    queryFn: () => getAdminTrends(params),
    refetchInterval: 30000,
  });
}
