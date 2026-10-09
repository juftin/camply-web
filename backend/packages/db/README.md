# camply-db

Database models and migrations for the camply platform.

## Checklist Data Layer Models

These models support the smart de-duplicated poller.

### User

Represents a platform user with early access flags and notification tokens.

- `id`: UUID (Primary Key)
- `auth0_id`: String (Unique, Nullable)
- `email`: String (Unique, Index)
- `is_invited`: Boolean (defaults to False; stored in the existing `is_early_access_user` column)
- `pushover_token`: String (Nullable)

### UniqueTarget

The de-duplicated "what" to scan. Represents a unique combination of provider, campground, and date range.

- `id`: UUID (Primary Key)
- `provider_id`: Integer (Foreign Key)
- `campground_id`: String (Foreign Key)
- `start_date`: Date
- `end_date`: Date
- `hash`: String (Unique Index) - SHA256 of composite fields, automatically calculated.

### UserScan

Links a user to a target with specific filtering preferences.

- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key)
- `target_id`: UUID (Foreign Key)
- `is_active`: Boolean (Defaults to True)
- `min_stay_length`: Integer
- `preferred_types`: ARRAY of Strings
- `require_electric`: Boolean

### ScanResult

Cached findings from a scan execution.

- `id`: UUID (Primary Key)
- `target_id`: UUID (Foreign Key)
- `campsite_id`: String
- `available_dates`: JSONB (Array of ISO date strings)
- `found_at`: Timestamp (Index)
