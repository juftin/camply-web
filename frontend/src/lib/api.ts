import axios, { AxiosError } from "axios";
import type {
  SearchResult,
  RecreationArea,
  Provider,
  Campground,
  MeResponse,
  MeUpdateRequest,
  ScanCreateRequest,
  ScanListResponse,
  ScanDetailResponse,
  ScanUpdateRequest,
  ScanResponse,
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
} from "@/lib/structs.ts";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const apiUrl = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: apiUrl || "/api",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Auth token interceptor (Basic auth takes priority over Bearer/Auth0)
// ---------------------------------------------------------------------------

let _getAccessToken: (() => Promise<string | null>) | null = null;
let _basicAuthHeader: string | null = null;

export function setAccessTokenProvider(fn: () => Promise<string | null>): void {
  _getAccessToken = fn;
}

/** Store HTTP Basic Auth credentials in memory (cleared on page refresh). */
export function setBasicAuth(username: string, password: string): void {
  _basicAuthHeader = `Basic ${btoa(`${username}:${password}`)}`;
}

/** Clear stored Basic Auth credentials (sign out). */
export function clearBasicAuth(): void {
  _basicAuthHeader = null;
}

api.interceptors.request.use(async (config) => {
  if (_basicAuthHeader) {
    config.headers.Authorization = _basicAuthHeader;
    return config;
  }
  if (_getAccessToken) {
    try {
      const token = await _getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // Silently skip — token retrieval may fail if not authenticated
    }
  }
  return config;
});

// Simple error helper
export function getApiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError && error.response?.data) {
    const detail = error.response.data.detail;
    if (typeof detail === "string") return detail;
    if (detail?.message) return detail.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred";
}

// ---------------------------------------------------------------------------
// Auth config
// ---------------------------------------------------------------------------

export interface AuthConfig {
  auth_mode: "basic" | "auth0";
  auth0_domain: string | null;
  auth0_client_id: string | null;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const response = await api.get<AuthConfig>("/auth-config");
  return response.data;
}

// ---------------------------------------------------------------------------
// Search & Metadata
// ---------------------------------------------------------------------------

export async function searchCampgrounds(
  query: string,
  limit: number = 20,
): Promise<SearchResult[]> {
  if (!query.trim()) return [];

  const response = await api.get<SearchResult[]>("/search", {
    params: { query: query.trim(), limit },
  });
  return response.data;
}

export async function getRecreationArea(
  provider: number,
  id: string,
): Promise<RecreationArea> {
  const response = await api.get<RecreationArea>(`/rec-area/${provider}/${id}`);
  return response.data;
}

export async function getProvider(id: number): Promise<Provider> {
  const response = await api.get<Provider>(`/provider/${id}`);
  return response.data;
}

export async function getCampgrounds(
  provider: number,
  recreationAreaId: string,
): Promise<Campground[]> {
  const response = await api.get<Campground[]>(
    `/rec-area/${provider}/${recreationAreaId}/campgrounds`,
  );
  return response.data;
}

export async function getCampground(
  provider: number,
  campgroundId: string,
): Promise<Campground> {
  const response = await api.get<Campground>(
    `/campground/${provider}/${campgroundId}`,
  );
  return response.data;
}

export async function listProviders(): Promise<Provider[]> {
  const response = await api.get<Provider[]>("/providers");
  return response.data;
}

// ---------------------------------------------------------------------------
// Auth / Profile
// ---------------------------------------------------------------------------

export interface AccessRequestPayload {
  email: string;
  name?: string | null;
}

export interface AccessRequestResponse {
  message: string;
}

export async function submitAccessRequest(
  payload: AccessRequestPayload,
): Promise<AccessRequestResponse> {
  const response = await api.post<AccessRequestResponse>(
    "/request-access",
    payload,
  );
  return response.data;
}

export async function getMe(): Promise<MeResponse> {
  const response = await api.get<MeResponse>("/me");
  return response.data;
}

export async function updateMe(payload: MeUpdateRequest): Promise<MeResponse> {
  const response = await api.patch<MeResponse>("/me", payload);
  return response.data;
}

// ---------------------------------------------------------------------------
// Scans
// ---------------------------------------------------------------------------

export async function listScans(params?: {
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<ScanListResponse> {
  const response = await api.get<ScanListResponse>("/scans", { params });
  return response.data;
}

export async function createScan(
  payload: ScanCreateRequest,
): Promise<ScanResponse> {
  const response = await api.post<ScanResponse>("/scans", payload);
  return response.data;
}

export async function getScan(scanId: string): Promise<ScanDetailResponse> {
  const response = await api.get<ScanDetailResponse>(`/scans/${scanId}`);
  return response.data;
}

export async function updateScan(
  scanId: string,
  payload: ScanUpdateRequest,
): Promise<ScanResponse> {
  const response = await api.patch<ScanResponse>(`/scans/${scanId}`, payload);
  return response.data;
}

export async function deleteScan(scanId: string): Promise<void> {
  await api.delete(`/scans/${scanId}`);
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export async function getAdminOverview(): Promise<AdminOverviewResponse> {
  const response = await api.get<AdminOverviewResponse>("/admin/overview");
  return response.data;
}

export async function listAdminUsers(params?: {
  search?: string;
  scanning_enabled?: boolean;
  limit?: number;
  offset?: number;
}): Promise<AdminUserListResponse> {
  const response = await api.get<AdminUserListResponse>("/admin/users", {
    params,
  });
  return response.data;
}

export async function getAdminUser(
  userId: string,
): Promise<AdminUserDetailResponse> {
  const response = await api.get<AdminUserDetailResponse>(
    `/admin/users/${userId}`,
  );
  return response.data;
}

export async function updateAdminUser(
  userId: string,
  payload: AdminUserUpdateRequest,
): Promise<AdminUserDetailResponse> {
  const response = await api.patch<AdminUserDetailResponse>(
    `/admin/users/${userId}`,
    payload,
  );
  return response.data;
}

export async function listAdminScans(params?: {
  owner_id?: string;
  is_active?: boolean;
  is_eligible?: boolean;
  provider_id?: number;
  limit?: number;
  offset?: number;
}): Promise<AdminScanListResponse> {
  const response = await api.get<AdminScanListResponse>("/admin/scans", {
    params,
  });
  return response.data;
}

export async function getAdminScan(
  scanId: string,
): Promise<AdminScanDetailResponse> {
  const response = await api.get<AdminScanDetailResponse>(
    `/admin/scans/${scanId}`,
  );
  return response.data;
}

export async function updateAdminScan(
  scanId: string,
  payload: AdminScanUpdateRequest,
): Promise<AdminScanDetailResponse> {
  const response = await api.patch<AdminScanDetailResponse>(
    `/admin/scans/${scanId}`,
    payload,
  );
  return response.data;
}

export async function getAdminTarget(
  targetId: string,
  params?: { limit?: number; offset?: number },
): Promise<AdminTargetDetailResponse> {
  const response = await api.get<AdminTargetDetailResponse>(
    `/admin/targets/${targetId}`,
    { params },
  );
  return response.data;
}

export async function listAdminAudit(params?: {
  limit?: number;
  offset?: number;
}): Promise<AdminAuditListResponse> {
  const response = await api.get<AdminAuditListResponse>("/admin/audit", {
    params,
  });
  return response.data;
}

export async function getAdminOperations(): Promise<AdminOperationsResponse> {
  const response = await api.get<AdminOperationsResponse>("/admin/operations");
  return response.data;
}

export async function listAdminOperationsTasks(params?: {
  limit?: number;
  offset?: number;
  task_name?: string;
  outcome?: string;
}): Promise<AdminOperationsTasksResponse> {
  const response = await api.get<AdminOperationsTasksResponse>(
    "/admin/operations/tasks",
    { params },
  );
  return response.data;
}

export async function getAdminOperationsTask(
  taskId: string,
): Promise<AdminOperationsTaskDetail> {
  const response = await api.get<AdminOperationsTaskDetail>(
    `/admin/operations/tasks/${taskId}`,
  );
  return response.data;
}

export async function getAdminTrends(params?: {
  group?: "usage" | "api" | "worker" | "provider";
  range?: "24h" | "7d" | "30d";
  endpoint?: string;
  task_name?: string;
  provider?: string;
}): Promise<AdminTrendsResponse> {
  const response = await api.get<AdminTrendsResponse>("/admin/trends", {
    params,
  });
  return response.data;
}
