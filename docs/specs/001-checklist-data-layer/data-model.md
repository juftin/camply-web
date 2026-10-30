# Data Model: Checklist Data Layer

## 1. `users` (New)

Represents a platform user.

- `id`: `UUID` (Primary Key, default=uuid4)
- `auth0_id`: `String(255)` (Unique, Nullable) - Auth0's `sub` identifier.
- `email`: `String(255)` (Unique, Index)
- `is_early_access_user`: `Boolean` (default=False)
- `pushover_token`: `String(255)` (Nullable) - User's notification token.
- `created_at`: `Timestamp`
- `updated_at`: `Timestamp`

## 2. `unique_targets` (New)

The de-duplicated "what" to scan.

- `id`: `UUID` (Primary Key, default=uuid4)
- `provider_id`: `Integer` (Foreign Key -> `providers.id`)
- `campground_id`: `String(255)` (Foreign Key -> `campgrounds.id`)
- `start_date`: `Date`
- `end_date`: `Date`
- `hash`: `String(64)` (Unique Index) - SHA256 of composite fields.
- `last_checked_at`: `Timestamp` (Nullable)
- `created_at`: `Timestamp`

## 3. `user_scans` (New)

The "who" and "how" of a scan request.

- `id`: `UUID` (Primary Key, default=uuid4)
- `user_id`: `UUID` (Foreign Key -> `users.id`)
- `target_id`: `UUID` (Foreign Key -> `unique_targets.id`)
- `is_active`: `Boolean` (default=True)
- `min_stay_length`: `Integer` (default=1)
- `preferred_types`: `ARRAY(String)` (Nullable) - e.g., ["TENT", "RV"]
- `require_electric`: `Boolean` (default=False)
- `created_at`: `Timestamp`
- `updated_at`: `Timestamp`

## 4. `scan_results` (New)

The ephemeral findings cache.

- `id`: `UUID` (Primary Key, default=uuid4)
- `target_id`: `UUID` (Foreign Key -> `unique_targets.id`)
- `campsite_id`: `String(255)` (Foreign Key -> `campsites.id`)
- `available_dates`: `JSONB` - Array of ISO date strings.
- `found_at`: `Timestamp` (Index)

## Relationships

- `User` has many `UserScan`
- `UniqueTarget` has many `UserScan`
- `UniqueTarget` has many `ScanResult`
- `Provider` has many `UniqueTarget`
- `Campground` has many `UniqueTarget`
