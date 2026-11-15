import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { validCoordinates, type GeoBounds } from "./maps";
import type {
  SearchResult,
  RecreationArea,
  Provider,
  Campground,
  CampgroundDetail,
  MeResponse,
  MeUpdateRequest,
  NotificationTestResponse,
  UserSessionListResponse,
  ScanCreateRequest,
  ScanListResponse,
  ScanDetailResponse,
  ScanUpdateRequest,
  ScanResponse,
  AdminOverviewResponse,
  AdminUserCreateRequest,
  AdminUserListResponse,
  AdminUserDetailResponse,
  AdminUserUpdateRequest,
  AdminAccessRequestItem,
  AdminAccessRequestListResponse,
  AdminAccessRequestUpdateRequest,
  ChangePasswordRequest,
  AdminScanListResponse,
  AdminScanDetailResponse,
  AdminScanUpdateRequest,
  AdminTargetDetailResponse,
  AdminAuditListResponse,
  AdminOperationsResponse,
  AdminOperationsTasksResponse,
  AdminOperationsTaskDetail,
  AdminSyncProvidersResponse,
  AdminTrendsResponse,
  SearchExploreResponse,
  SearchMapSummary,
  SearchMapResponse,
  SearchMapMembers,
} from "@/lib/structs.ts";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------

const apiUrl = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: apiUrl || "/api",
  timeout: 10000,
  withCredentials: true,
  xsrfCookieName: "camply_csrf",
  xsrfHeaderName: "X-CSRF-Token",
  withXSRFToken: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// ---------------------------------------------------------------------------
// Token acquisition classification & bearer/renewal interceptors
// ---------------------------------------------------------------------------

export type TokenAcquisitionErrorKind = "expired" | "outage" | "auth_failure";

export class TokenAcquisitionError extends Error {
  readonly kind: TokenAcquisitionErrorKind;
  readonly code?: string;

  constructor(kind: TokenAcquisitionErrorKind, message: string, code?: string) {
    super(message);
    this.name = "TokenAcquisitionError";
    this.kind = kind;
    this.code = code;
  }
}

const EXPIRED_TOKEN_ERROR_CODES = new Set([
  "login_required",
  "consent_required",
  "interaction_required",
  "missing_refresh_token",
  "invalid_grant",
]);

const OUTAGE_TOKEN_ERROR_CODES = new Set([
  "timeout",
  "server_error",
  "temporarily_unavailable",
  "err_network",
  "econnaborted",
  "etimedout",
  "econnrefused",
]);

const SAFE_IDEMPOTENT_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

function readErrorField(error: unknown, key: string): unknown {
  if (typeof error === "object" && error !== null && key in error) {
    return (error as Record<string, unknown>)[key];
  }
  return undefined;
}

/** Classify token acquisition failures into expired session, IdP outage, or auth failure. */
export function classifyTokenAcquisitionError(
  error: unknown,
): TokenAcquisitionError {
  if (error instanceof TokenAcquisitionError) {
    return error;
  }

  const rawCode =
    readErrorField(error, "error") ?? readErrorField(error, "code");
  const code =
    typeof rawCode === "string" && rawCode.trim() ? rawCode.trim() : undefined;
  const normalizedCode = code?.toLowerCase();

  const rawDescription = readErrorField(error, "error_description");
  const description =
    typeof rawDescription === "string" && rawDescription.trim()
      ? rawDescription.trim()
      : undefined;

  const message =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : "";
  const normalizedMessage = message.toLowerCase();
  const normalizedName = error instanceof Error ? error.name.toLowerCase() : "";

  const rawStatus =
    readErrorField(error, "status") ??
    readErrorField(error, "statusCode") ??
    readErrorField(readErrorField(error, "response"), "status");
  const status = typeof rawStatus === "number" ? rawStatus : undefined;

  if (
    (normalizedCode && EXPIRED_TOKEN_ERROR_CODES.has(normalizedCode)) ||
    normalizedName === "missingrefreshtokenerror" ||
    /login_required|consent_required|interaction_required|missing_refresh_token|invalid_grant/.test(
      normalizedMessage,
    )
  ) {
    return new TokenAcquisitionError(
      "expired",
      "Your session has expired. Please sign in again.",
      code,
    );
  }

  if (
    (normalizedCode && OUTAGE_TOKEN_ERROR_CODES.has(normalizedCode)) ||
    (status !== undefined && status >= 500 && status < 600) ||
    normalizedName === "timeouterror" ||
    /failed to fetch|networkerror|network error|network request failed|load failed|timed out|timeout|econnrefused|enotfound|err_network|temporarily unavailable|service unavailable|\b50[0234]\b/.test(
      normalizedMessage,
    ) ||
    (description !== undefined &&
      /temporarily unavailable|timeout|service unavailable/.test(
        description.toLowerCase(),
      ))
  ) {
    return new TokenAcquisitionError(
      "outage",
      "The authentication service is temporarily unavailable. Please try again shortly.",
      code,
    );
  }

  let authFailureMessage = "Authentication failed. Please sign in again.";
  if (normalizedCode === "access_denied") {
    authFailureMessage =
      description ?? "Access was denied by the authentication provider.";
  } else if (normalizedCode === "invalid_scope") {
    authFailureMessage =
      description ?? "Authentication permissions could not be verified.";
  } else if (description) {
    authFailureMessage = description;
  } else if (message && message !== "Error") {
    authFailureMessage = message;
  }

  return new TokenAcquisitionError("auth_failure", authFailureMessage, code);
}

/** Guard protected queries against retrying terminal auth, access, or conflict errors. */
export function shouldRetryProtectedQuery(
  failureCount: number,
  error: unknown,
): boolean {
  if (failureCount >= 1) {
    return false;
  }
  if (error instanceof TokenAcquisitionError) {
    return error.kind === "outage";
  }
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 401 || status === 403 || status === 409) {
      return false;
    }
    return status === undefined || status >= 500;
  }
  return true;
}

export interface AccessTokenRequestOptions {
  cacheMode?: "on" | "off" | "cache-only";
}

export type AccessTokenProvider = (
  options?: AccessTokenRequestOptions,
) => Promise<string | null>;

export interface AuthFailureCallbacks {
  onSessionExpired?: (error: TokenAcquisitionError) => void;
  onAuthFailure?: (error: TokenAcquisitionError) => void;
  onOutage?: (error: TokenAcquisitionError) => void;
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retried?: boolean;
}

let _authMode: AuthConfig["auth_mode"] = "none";
let _getAccessToken: AccessTokenProvider | null = null;
let _authCallbacks: AuthFailureCallbacks = {};
let _inflightRefresh: Promise<string | null> | null = null;

export function setApiAuthMode(mode: AuthConfig["auth_mode"]): void {
  _authMode = mode;
}

export function setAccessTokenProvider(
  fn: AccessTokenProvider | null,
  callbacks?: AuthFailureCallbacks,
): void {
  _getAccessToken = fn;
  _authCallbacks = callbacks ?? {};
  _inflightRefresh = null;
}

function isSafeIdempotentMethod(method?: string): boolean {
  return SAFE_IDEMPOTENT_METHODS.has((method ?? "GET").toUpperCase());
}

function hasAuthorizationHeader(
  headers:
    | InternalAxiosRequestConfig["headers"]
    | Record<string, string>
    | undefined,
): boolean {
  if (!headers) return false;
  if (typeof (headers as { get?: unknown }).get === "function") {
    return Boolean(
      (headers as { get: (name: string) => unknown }).get("Authorization"),
    );
  }
  const record = headers as Record<string, unknown>;
  return Boolean(record.Authorization ?? record.authorization);
}

function setBearerHeader(
  headers:
    | InternalAxiosRequestConfig["headers"]
    | Record<string, string>
    | undefined,
  token: string,
): Record<string, string> {
  const value = `Bearer ${token}`;
  if (headers && typeof (headers as { set?: unknown }).set === "function") {
    (headers as { set: (name: string, val: string) => void }).set(
      "Authorization",
      value,
    );
    return headers as unknown as Record<string, string>;
  }
  const target = (headers ?? {}) as Record<string, string>;
  target.Authorization = value;
  return target;
}

function notifyClassifiedError(error: TokenAcquisitionError): void {
  if (error.kind === "expired") {
    _authCallbacks.onSessionExpired?.(error);
  } else if (error.kind === "auth_failure") {
    _authCallbacks.onAuthFailure?.(error);
  } else {
    _authCallbacks.onOutage?.(error);
  }
}

async function acquireAccessToken(
  options?: AccessTokenRequestOptions,
): Promise<string | null> {
  if (!_getAccessToken) return null;

  if (options?.cacheMode === "off") {
    if (!_inflightRefresh) {
      _inflightRefresh = _getAccessToken({ cacheMode: "off" }).finally(() => {
        _inflightRefresh = null;
      });
    }
    return _inflightRefresh;
  }

  return _getAccessToken(options);
}

api.interceptors.request.use(async (config) => {
  const retryConfig = config as RetryableRequestConfig;
  if (
    _getAccessToken &&
    !(retryConfig._retried && hasAuthorizationHeader(config.headers))
  ) {
    try {
      const token = await acquireAccessToken();
      if (token) {
        config.headers = setBearerHeader(
          config.headers,
          token,
        ) as InternalAxiosRequestConfig["headers"];
      }
    } catch (error) {
      const classified = classifyTokenAcquisitionError(error);
      notifyClassifiedError(classified);
      return Promise.reject(classified);
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || !error.config) {
      return Promise.reject(error);
    }

    const originalRequest = error.config as RetryableRequestConfig;
    const status = error.response?.status;

    if (status === 401 && _authMode === "auth0" && _getAccessToken !== null) {
      if (
        !isSafeIdempotentMethod(originalRequest.method) ||
        originalRequest._retried
      ) {
        _authCallbacks.onSessionExpired?.(
          new TokenAcquisitionError(
            "expired",
            isSafeIdempotentMethod(originalRequest.method)
              ? "Your session has expired. Please sign in again."
              : "Your session expired. Please sign in again before retrying this action.",
          ),
        );
        return Promise.reject(error);
      }

      originalRequest._retried = true;
      try {
        const refreshedToken = await acquireAccessToken({ cacheMode: "off" });
        if (!refreshedToken) {
          const expiredError = new TokenAcquisitionError(
            "expired",
            "Your session has expired. Please sign in again.",
          );
          _authCallbacks.onSessionExpired?.(expiredError);
          return Promise.reject(expiredError);
        }
        originalRequest.headers = setBearerHeader(
          originalRequest.headers,
          refreshedToken,
        ) as InternalAxiosRequestConfig["headers"];
        return await api.request(originalRequest);
      } catch (refreshError) {
        const classified = classifyTokenAcquisitionError(refreshError);
        notifyClassifiedError(classified);
        return Promise.reject(classified);
      }
    }

    return Promise.reject(error);
  },
);

// Simple error helper
export function getApiErrorMessage(error: unknown): string {
  if (error instanceof TokenAcquisitionError) {
    return error.message;
  }
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (
      detail &&
      typeof detail === "object" &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
    if (error.response?.status === 503) {
      return "Verification service is temporarily unavailable. Please try again shortly.";
    }
    if (error.response?.status === 401) {
      return "Your session has expired. Please sign in again.";
    }
    if (!error.response && error.message) {
      return error.message;
    }
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred";
}

// ---------------------------------------------------------------------------
// Auth config
// ---------------------------------------------------------------------------

export interface AuthConfig {
  auth_mode: "none" | "session" | "auth0";
  auth0_domain: string | null;
  auth0_client_id: string | null;
  auth0_audience: string | null;
  invite_only: boolean;
  auto_login: boolean;
  signup_enabled: boolean;
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
  signal?: AbortSignal,
): Promise<SearchResult[]> {
  if (!query.trim()) return [];

  const response = await api.get<SearchResult[]>("/search", {
    params: { query: query.trim(), limit },
    signal,
  });
  return response.data;
}

/** Resolve only approximate public coordinates without application credentials. */
export async function locateByIp(
  signal?: AbortSignal,
): Promise<{ lat: number; lng: number } | null> {
  try {
    const response = await axios.get<{
      latitude?: number;
      longitude?: number;
      error?: boolean;
    }>("https://ipapi.co/json/", {
      signal,
      timeout: 2500,
      withCredentials: false,
      withXSRFToken: false,
    });
    const { latitude, longitude, error } = response.data;
    return !error && validCoordinates(latitude, longitude)
      ? { lat: latitude!, lng: longitude! }
      : null;
  } catch {
    return null;
  }
}

export interface SearchExploreParams {
  bounds?: GeoBounds;
  query?: string;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  providerId?: number;
  entityType?: string;
  state?: string;
  hasElectric?: boolean;
  petsAllowed?: boolean;
  minRvLength?: number;
  lat?: number;
  lng?: number;
  radiusMiles?: number;
}

export function exploreQueryParams(
  params: SearchExploreParams = {},
): Record<string, string | number | boolean> {
  const queryParams: Record<string, string | number | boolean> = {};
  if (params.query?.trim()) queryParams.q = params.query.trim();
  if (params.page !== undefined) queryParams.page = params.page;
  if (params.pageSize !== undefined) queryParams.page_size = params.pageSize;
  if (params.sortBy) queryParams.sort_by = params.sortBy;
  if (params.providerId !== undefined)
    queryParams.provider_id = params.providerId;
  if (params.entityType) queryParams.entity_type = params.entityType;
  if (params.state) queryParams.state = params.state;
  if (params.hasElectric !== undefined)
    queryParams.has_electric = params.hasElectric;
  if (params.petsAllowed !== undefined)
    queryParams.pets_allowed = params.petsAllowed;
  if (params.minRvLength !== undefined)
    queryParams.min_rv_length = params.minRvLength;
  if (params.lat !== undefined) queryParams.lat = params.lat;
  if (params.lng !== undefined) queryParams.lng = params.lng;
  if (params.radiusMiles !== undefined)
    queryParams.radius_miles = params.radiusMiles;

  if (params.bounds) Object.assign(queryParams, params.bounds);
  return queryParams;
}

export function mapQueryParams(params: SearchExploreParams = {}) {
  const result = exploreQueryParams({ ...params, bounds: undefined });
  delete result.page;
  delete result.page_size;
  delete result.sort_by;
  return result;
}

export async function searchExplore(
  params: SearchExploreParams = {},
  signal?: AbortSignal,
): Promise<SearchExploreResponse> {
  const queryParams = exploreQueryParams(params);
  const response = await api.get<SearchExploreResponse>("/search/explore", {
    params: queryParams,
    signal,
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
): Promise<CampgroundDetail> {
  const response = await api.get<CampgroundDetail>(
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

/** Sign in and verify that the browser retained the HTTP-only session. */
export async function loginSession(
  username: string,
  password: string,
): Promise<MeResponse> {
  await api.post<MeResponse>("/login", { username, password });
  try {
    return await getMe();
  } catch (error) {
    if (error instanceof AxiosError && error.response?.status === 401) {
      throw new Error(
        "Your session cookie could not be verified. Check browser cookie settings and that the frontend and API are served from the same site.",
      );
    }
    throw error;
  }
}

/** End the cookie session without storing credentials in the frontend. */
export async function logoutSession(): Promise<void> {
  await api.post("/logout");
}

export async function changePassword(
  payload: ChangePasswordRequest,
): Promise<MeResponse> {
  const response = await api.post<MeResponse>("/change-password", payload);
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

export async function sendTestNotification(
  payload: MeUpdateRequest,
): Promise<NotificationTestResponse> {
  try {
    const response = await api.post<NotificationTestResponse>(
      "/me/notifications/test",
      payload,
      { timeout: 30000 },
    );
    return response.data;
  } catch (error) {
    if (
      axios.isAxiosError<{ detail?: unknown }>(error) &&
      typeof error.response?.data.detail === "string"
    ) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(
      "Could not send the test notification. Check your settings and try again.",
    );
  }
}

export async function listMySessions(): Promise<UserSessionListResponse> {
  const response = await api.get<UserSessionListResponse>("/me/sessions");
  return response.data;
}

export async function revokeMySession(sessionId: string): Promise<void> {
  await api.delete(`/me/sessions/${sessionId}`);
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
  is_invited?: boolean;
  limit?: number;
  offset?: number;
}): Promise<AdminUserListResponse> {
  const response = await api.get<AdminUserListResponse>("/admin/users", {
    params,
  });
  return response.data;
}

export async function listAdminAccessRequests(params?: {
  status?: "pending" | "approved" | "rejected";
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<AdminAccessRequestListResponse> {
  const response = await api.get<AdminAccessRequestListResponse>(
    "/admin/access-requests",
    { params },
  );
  return response.data;
}

export async function updateAdminAccessRequest(
  requestId: string,
  payload: AdminAccessRequestUpdateRequest,
): Promise<AdminAccessRequestItem> {
  const response = await api.patch<AdminAccessRequestItem>(
    `/admin/access-requests/${requestId}`,
    payload,
  );
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

export async function createAdminUser(
  payload: AdminUserCreateRequest,
): Promise<AdminUserDetailResponse> {
  const response = await api.post<AdminUserDetailResponse>(
    "/admin/users",
    payload,
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
  target_status?: "active" | "overdue" | "dormant";
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
  provider?: string;
  search?: string;
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

export async function syncAdminProviders(): Promise<AdminSyncProvidersResponse> {
  const response = await api.post<AdminSyncProvidersResponse>(
    "/admin/operations/sync-providers",
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

export async function searchMapSummary(
  params: SearchExploreParams,
  signal?: AbortSignal,
): Promise<SearchMapSummary> {
  return (
    await api.get<SearchMapSummary>("/search/map/summary", {
      params: mapQueryParams(params),
      signal,
    })
  ).data;
}
export async function searchMap(
  params: SearchExploreParams,
  bounds: import("./maps").GeoBounds,
  zoom: number,
  signal?: AbortSignal,
): Promise<SearchMapResponse> {
  return (
    await api.get<SearchMapResponse>("/search/map", {
      params: { ...mapQueryParams(params), ...bounds, zoom },
      signal,
    })
  ).data;
}
export async function searchMapMembers(
  params: SearchExploreParams,
  bounds: import("./maps").GeoBounds,
  cellId: string,
  afterId?: string,
  signal?: AbortSignal,
): Promise<SearchMapMembers> {
  return (
    await api.get<SearchMapMembers>("/search/map/members", {
      params: {
        ...mapQueryParams(params),
        ...bounds,
        cell_id: cellId,
        after_id: afterId,
      },
      signal,
    })
  ).data;
}
