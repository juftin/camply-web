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
  is_early_access_user: boolean;
  pushover_token: string | null;
}

export interface MeUpdateRequest {
  pushover_token?: string | null;
}

// ---- Scans ----

export interface ScanCreateRequest {
  provider_id: number;
  campground_id: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
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
