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
}

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

export interface AdminOverviewResponse {
  total_users: number;
  scanning_enabled_users: number;
  suspended_users: number;
  total_scans: number;
  saved_active_scans: number;
  eligible_scans: number;
  unique_targets: number;
  eligible_targets: number;
  dormant_targets: number;
  overdue_targets: number;
  heartbeat_interval_seconds: number;
  target_cooldown_seconds: number;
}

export interface AdminUserItem {
  id: string;
  email: string;
  auth0_id: string | null;
  is_admin: boolean;
  is_invited: boolean;
  scanning_enabled: boolean;
  has_pushover_token: boolean;
  total_scans: number;
  active_scans: number;
  created_at: string;
  updated_at: string;
}

export interface AdminUserListResponse {
  users: AdminUserItem[];
  total: number;
}

export interface AdminUserDetailResponse {
  id: string;
  email: string;
  auth0_id: string | null;
  is_admin: boolean;
  is_invited: boolean;
  scanning_enabled: boolean;
  has_pushover_token: boolean;
  total_scans: number;
  active_scans: number;
  created_at: string;
  updated_at: string;
}

export interface AdminUserUpdateRequest {
  scanning_enabled: boolean;
}

export interface AdminScanItem {
  id: string;
  user_id: string;
  user_email: string;
  target_id: string;
  provider_id: number;
  campground_id: string;
  campground_name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  is_eligible: boolean;
  user_scanning_enabled: boolean;
  min_stay_length: number;
  preferred_types: string[];
  require_electric: boolean;
  last_checked_at: string | null;
  found_count: number;
  created_at: string;
}

export interface AdminScanListResponse {
  scans: AdminScanItem[];
  total: number;
}

export interface AdminScanDetailResponse extends AdminScanItem {
  results: ScanResultItem[];
}

export interface AdminScanUpdateRequest {
  is_active: boolean;
}

export interface AdminTargetSubscriberItem {
  scan_id: string;
  user_id: string;
  user_email: string;
  is_active: boolean;
  is_eligible: boolean;
  user_scanning_enabled: boolean;
  created_at: string;
}

export interface AdminTargetDetailResponse {
  id: string;
  provider_id: number;
  campground_id: string;
  campground_name: string;
  start_date: string;
  end_date: string;
  hash: string;
  last_checked_at: string | null;
  created_at: string;
  total_subscribers: number;
  eligible_subscribers: number;
  status: string;
  subscribers: AdminTargetSubscriberItem[];
  subscribers_total: number;
}

export interface AdminAuditEventItem {
  id: string;
  actor_id: string;
  actor_email: string;
  action: string;
  subject_type: string;
  subject_id: string;
  prev_value: boolean | null;
  new_value: boolean | null;
  created_at: string;
}

export interface AdminAuditListResponse {
  events: AdminAuditEventItem[];
  total: number;
}

export interface AdminWorkerItem {
  name: string;
  status: string;
  active_tasks: number;
  reserved_tasks: number;
  scheduled_tasks: number;
}

export interface AdminDiscoveryMetadata {
  timestamp: string;
  targets_discovered: number;
  targets_enqueued: number;
  status: string;
}

export interface AdminOperationsResponse {
  workers: AdminWorkerItem[];
  queue_depth: number;
  active_tasks_total: number;
  reserved_tasks_total: number;
  scheduled_tasks_total: number;
  last_discovery: AdminDiscoveryMetadata | null;
  broker_connected: boolean;
  snapshot_at: string;
}

export interface AdminTaskTelemetryItem {
  task_id: string;
  task_name: string;
  worker: string;
  finished_at: string;
  duration_ms: number;
  entity_type: string | null;
  entity_id: string | null;
  outcome: string;
  reason: string | null;
}

export interface AdminOperationsTasksResponse {
  tasks: AdminTaskTelemetryItem[];
  total: number;
}

export interface AdminOperationsTaskDetail {
  task_id: string;
  task_name: string;
  worker: string;
  finished_at: string;
  duration_ms: number;
  entity_type: string | null;
  entity_id: string | null;
  outcome: string;
  reason: string | null;
}

export interface TrendPoint {
  timestamp: string;
  value: number;
}

export interface TrendSeries {
  name: string;
  labels: Record<string, string>;
  points: TrendPoint[];
}

export interface TrendMetric {
  metric_id: string;
  title: string;
  description: string;
  unit: string;
  chart_type: "line" | "bar" | "stat";
  series: TrendSeries[];
}

export interface AdminTrendsResponse {
  group: string;
  range: string;
  step_seconds: number;
  start_time: string;
  end_time: string;
  timezone: string;
  available: boolean;
  error_message: string | null;
  metrics: TrendMetric[];
}
