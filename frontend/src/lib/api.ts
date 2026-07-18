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
// Auth token interceptor
// ---------------------------------------------------------------------------

let _getAccessToken: (() => Promise<string | null>) | null = null;

export function setAccessTokenProvider(fn: () => Promise<string | null>): void {
  _getAccessToken = fn;
}

api.interceptors.request.use(async (config) => {
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
  const response = await api.post<AccessRequestResponse>("/request-access", payload);
  return response.data;
}

export async function getMe(): Promise<MeResponse> {
  const response = await api.get<MeResponse>("/me");
  return response.data;
}

export async function updateMe(
  payload: MeUpdateRequest,
): Promise<MeResponse> {
  const response = await api.patch<MeResponse>("/me", payload);
  return response.data;
}

// ---------------------------------------------------------------------------
// Scans
// ---------------------------------------------------------------------------

export async function listScans(
  params?: { is_active?: boolean; limit?: number; offset?: number },
): Promise<ScanListResponse> {
  const response = await api.get<ScanListResponse>("/scans", { params });
  return response.data;
}

export async function createScan(
  payload: ScanCreateRequest,
): Promise<ScanResponse> {
  const response = await api.post<ScanResponse>("/scans", payload);
  return response.data;
}

export async function getScan(
  scanId: string,
): Promise<ScanDetailResponse> {
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
