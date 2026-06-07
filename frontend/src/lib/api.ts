// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

import axios, { AxiosError } from "axios";
import type {
  SearchResult,
  RecreationArea,
  Provider,
  Campground,
  MeResponse,
  ScanCreateRequest,
  ScanListResponse,
  ScanDetailResponse,
  ScanUpdateRequest,
  ScanResponse,
  AccessRequestResponse,
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

// Inject Auth0 bearer token when available
function getAccessToken(): string | null {
  try {
    // Dynamic import to avoid crash when @auth0/auth0-react isn't loaded
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
    if (!auth0Domain) return null;
    // @ts-expect-error — auth0 is available at runtime
    const cache = (window as any).__auth0_cache__;
    return cache?.accessToken ?? null;
  } catch {
    return null;
  }
}

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
// Auth0 token interceptor
// ---------------------------------------------------------------------------

// Store a reference to the Auth0 getAccessTokenSilently function so the
// API layer can refresh the token without depending on React context.
let _getAuth0Token: (() => Promise<string | null>) | null = null;

export function setAuth0TokenProvider(
  provider: () => Promise<string | null>,
): void {
  _getAuth0Token = provider;
}

api.interceptors.request.use(async (config) => {
  if (_getAuth0Token) {
    const token = await _getAuth0Token();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

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

export async function getMe(): Promise<MeResponse> {
  const response = await api.get<MeResponse>("/me");
  return response.data;
}

export async function updateMe(payload: {
  pushover_token?: string | null;
}): Promise<MeResponse> {
  const response = await api.patch<MeResponse>("/me", payload);
  return response.data;
}

// ---------------------------------------------------------------------------
// Access Requests
// ---------------------------------------------------------------------------

export async function requestAccess(
  email: string,
): Promise<AccessRequestResponse> {
  const response = await api.post<AccessRequestResponse>("/request-access", {
    email,
  });
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

export async function getScan(scanId: string): Promise<ScanDetailResponse> {
  const response = await api.get<ScanDetailResponse>(`/scans/${scanId}`);
  return response.data;
}

export async function updateScanApi(
  scanId: string,
  payload: ScanUpdateRequest,
): Promise<ScanResponse> {
  const response = await api.patch<ScanResponse>(`/scans/${scanId}`, payload);
  return response.data;
}

export async function deleteScan(scanId: string): Promise<void> {
  await api.delete(`/scans/${scanId}`);
}

export { api as axiosInstance };
