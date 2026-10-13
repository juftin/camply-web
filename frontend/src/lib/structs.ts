import type { components } from "./api/generated/schema";

// =========================================================================
// Shared type definitions matching the backend API.
// =========================================================================

export interface SearchResult {
  id: string;
  entity_type: string;
  provider_id: number;
  provider_name: string;
  recreation_area_id: string | null;
  recreation_area_name: string | null;
  campground_id: string | null;
  campground_name: string | null;
}

export interface RecreationArea {
  id: string;
  provider_id: number;
  name: string;
  description: string | null;
  country: string | null;
  state: string | null;
  longitude: number | null;
  latitude: number | null;
  reservable: boolean;
  enabled: boolean;
  url: string;
}

export interface Provider {
  id: number;
  name: string;
  description: string | null;
  url: string;
  enabled: boolean;
}

export interface Campground {
  id: string;
  provider_id: number;
  recreation_area_id: string | null;
  name: string;
  description: string | null;
  country: string | null;
  state: string | null;
  longitude: number | null;
  latitude: number | null;
  reservable: boolean;
  enabled: boolean;
  url: string;
}

// ---- Auth / Profile ----

export interface MeResponse {
  id: string;
  email: string;
  is_invited: boolean;
  is_admin: boolean;
  scanning_enabled: boolean;
  pushover_token: string | null;
  must_change_password?: boolean;
}

export type ChangePasswordRequest =
  components["schemas"]["ChangePasswordRequest"];

export interface MeUpdateRequest {
  pushover_token?: string | null;
}

// ---- Scans ----

export interface ScanCreateRequest {
  provider_id: number;
  campground_id: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  min_stay_length?: number;
  preferred_types?: string[];
  require_electric?: boolean;
}

export interface ScanUpdateRequest {
  is_active?: boolean;
  min_stay_length?: number;
  preferred_types?: string[];
  require_electric?: boolean;
}

export interface ScanResultItem {
  campsite_id: string;
  campsite_name: string;
  available_dates: string[];
}

export interface ScanResponse {
  id: string;
  provider_id: number;
  campground_id: string;
  campground_name: string;
  recreation_area_name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  min_stay_length: number;
  preferred_types: string[];
  require_electric: boolean;
  last_checked_at: string | null;
  found_count: number;
  created_at: string;
}

export interface ScanListResponse {
  scans: ScanResponse[];
  total: number;
}

export interface ScanDetailResponse extends ScanResponse {
  results: ScanResultItem[];
}

// ---- Error responses ----

export interface ApiError {
  detail: string | { error: string; message: string };
}

// ---- Admin UI ----

export type AdminOverviewResponse =
  components["schemas"]["AdminOverviewResponse"];
export type AdminUserItem = components["schemas"]["AdminUserItem"];
export type AdminUserListResponse =
  components["schemas"]["AdminUserListResponse"];
export type AdminUserDetailResponse =
  components["schemas"]["AdminUserDetailResponse"];
export type AdminUserCreateRequest =
  components["schemas"]["AdminUserCreateRequest"];
export type AdminUserUpdateRequest =
  components["schemas"]["AdminUserUpdateRequest"];
export type AdminScanItem = components["schemas"]["AdminScanItem"];
export type AdminScanListResponse =
  components["schemas"]["AdminScanListResponse"];
export type AdminScanDetailResponse =
  components["schemas"]["AdminScanDetailResponse"];
export type AdminScanUpdateRequest =
  components["schemas"]["AdminScanUpdateRequest"];
export type AdminTargetSubscriberItem =
  components["schemas"]["AdminTargetSubscriberItem"];
export type AdminTargetDetailResponse =
  components["schemas"]["AdminTargetDetailResponse"];
export type AdminAuditEventItem = components["schemas"]["AdminAuditEventItem"];
export type AdminAuditListResponse =
  components["schemas"]["AdminAuditListResponse"];
export type AdminWorkerItem = components["schemas"]["AdminWorkerItem"];
export type AdminDiscoveryMetadata =
  components["schemas"]["AdminDiscoveryMetadata"];
export type AdminOperationsResponse =
  components["schemas"]["AdminOperationsResponse"];
export type AdminTaskTelemetryItem =
  components["schemas"]["AdminTaskTelemetryItem"];
export type AdminOperationsTasksResponse =
  components["schemas"]["AdminOperationsTasksResponse"];
export type AdminOperationsTaskDetail =
  components["schemas"]["AdminOperationsTaskDetail"];
export type TrendPoint = components["schemas"]["TrendPoint"];
export type TrendSeries = components["schemas"]["TrendSeries"];
export type TrendMetric = components["schemas"]["TrendMetric"];
export type AdminTrendsResponse = components["schemas"]["AdminTrendsResponse"];
