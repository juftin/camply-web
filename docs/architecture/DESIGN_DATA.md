# Data Model

camply shares one SQLAlchemy model set and Alembic migration graph (`camply.db`) across both SQLite (standalone) and PostgreSQL (distributed).

## Storage boundaries

`camply.db` depends only on base package dependencies plus the optional `postgres` extra (`psycopg`). It never imports `camply.server` or `camply.worker`.

In standalone mode, SQLite runs with foreign keys enabled, WAL journaling, and a 1,000 ms busy timeout. Long-running provider and notification HTTP calls stay outside database write transactions.

## Core data hierarchy

Provider-owned records use composite keys `(id, provider_id)` so native IDs from different reservation systems never collide:

1. **`providers`:** Supported booking services and a monotonic `catalog_revision` counter.
2. **`recreation_areas`:** Parks or regions with optional descriptions, locations, and cached `DestinationDetails` JSON.
3. **`campgrounds`:** Bookable facilities linked to a parent recreation area and provider, with discovery capability columns (`campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`).
4. **`search`:** Denormalized catalog view (`EntityType/ProviderID/RecAreaID/CampgroundID`) carrying aggregated discovery capabilities for Explore and autocomplete.

On PostgreSQL, `search` uses a weighted `simple`-dictionary full-text vector (`pg_trgm` + GIN indexes) maintained transactionally on catalog sync. On SQLite, search falls back to portable substring matching.

## Polling, subscriptions, and results

- **`unique_targets`:** Shared polling targets keyed by a SHA-256 hash of `(provider_id, campground_id, start_date, end_date)` with `last_checked_at`.
- **`user_scans`:** User subscriptions storing `destination_type` (`campground` or `recreation_area`), `coverage_mode` (`all` or `selected`), date range, `definition_hash`, monotonic version counters (`definition_revision`, `coverage_revision`, `row_version`), and fail-closed filters (`min_stay_length`, `preferred_types`, `require_electric`, `require_accessible`, `min_rv_length`, `allowed_weekdays`).
- **`scan_targets`:** Maps recreation-area `UserScan` rows to member `UniqueTarget` rows, tracking per-round outcomes (`pending`, `retrying`, `success`, `failed`).
- **`scan_results`:** Latest successful campsite availability snapshot per `unique_target`, storing site name, standardized type, electric/accessibility flags, `permitted_equipment`, `max_vehicle_length`, `available_dates`, and `found_at`.

Successful empty checks clear `scan_results`; failed checks keep the prior snapshot. User-facing queries and alerts discard nights before the current UTC day and outside the scan window before evaluating filters, `allowed_weekdays`, and `min_stay_length`.

## Delivery, auth, and access tables

- **`notification_outbox`:** Durable standalone delivery queue storing credential-free JSON payloads, `payload_kind` (`campground` or `area`), `scan_revision`, `delivery_key`, attempt counts (`0–4`), and allowlisted error categories. Terminal rows expire after 24 hours; pending retries survive restarts.
- **`users` and `user_sessions`:** User accounts (linked via `auth0_id` or local session auth), invitation flags (`is_early_access_user` mapped to `is_invited`), notification settings, and revocable session `jti` rows.
- **`access_requests`:** Invite-only access requests (`pending`, `approved`, `rejected`) linked to reviewing admins and resulting user accounts.
