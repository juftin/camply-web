# Data Model: Equipment Metadata and Filtering

**Feature**: `030-equipment-metadata-filtering`
**Date**: 2026-11-16
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## 1. Provider DTO (`src/camply/providers/dto.py`)

### `CampsiteDTO`

Add normalized equipment and length capability fields while keeping existing fields unchanged:

| Field                 | Type          | Default | Semantics                                                                                                        |
| --------------------- | ------------- | ------- | ---------------------------------------------------------------------------------------------------------------- |
| `permitted_equipment` | `list[str]`   | `[]`    | Normalized unique equipment labels permitted on the site (e.g. `["RV", "Trailer", "Tent"]`)                      |
| `max_vehicle_length`  | `int \| None` | `None`  | Maximum compatible RV/trailer/vehicle length in whole feet (`> 0` when known, `None` when unknown or unverified) |

**Validation / Normalization**:

- Positive integers only for `max_vehicle_length`; upstream `0`, negative, or missing values normalize to `None`.
- Fractional or metric upstream lengths are floored conservatively to whole feet before constructing `CampsiteDTO`.

---

## 2. Persistence Models (`src/camply/db/models/`)

### `Campground` (`campgrounds` table)

Add discovery capability columns populated atomically by provider catalog sync (`populate_database`) and enrichment backfills:

| Column           | SQL Type                                       | Nullable / Default                                      | Constraint / Notes                                                                                  |
| ---------------- | ---------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `campsite_types` | `ARRAY(String).with_variant(JSON(), "sqlite")` | `nullable=True`                                         | Distinct standardized site types (`TENT`, `RV`, `CABIN`, `OTHER`)                                   |
| `has_electric`   | `Boolean`                                      | `nullable=False, default=False, server_default=false()` | True only when verified by provider catalog or site metadata                                        |
| `has_water`      | `Boolean`                                      | `nullable=False, default=False, server_default=false()` | True only when verified                                                                             |
| `has_sewer`      | `Boolean`                                      | `nullable=False, default=False, server_default=false()` | True only when verified                                                                             |
| `pets_allowed`   | `Boolean`                                      | `nullable=False, default=False, server_default=false()` | True only when verified                                                                             |
| `ada_accessible` | `Boolean`                                      | `nullable=False, default=False, server_default=false()` | True only when verified                                                                             |
| `max_rv_length`  | `Integer`                                      | `nullable=True`                                         | `CheckConstraint("max_rv_length IS NULL OR max_rv_length > 0", name="ck_campground_max_rv_length")` |

### `Search` (`search` table)

Existing columns (`campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`) remain unchanged in schema and indexes:

- Campground rows copy `Campground` capability columns directly during `BaseProvider.populate_search_table`.
- Recreation-area rows aggregate `BOOL_OR` equivalents (`any`) and `MAX(max_rv_length)` plus unioned `campsite_types` across enabled, reservable child `Campground` rows.
- `Search.search()` adds `ada_accessible: bool | None = None` filter parameter (`filters.append(cls.ada_accessible.is_(ada_accessible))` when provided).

### `ScanResult` (`scan_results` table)

Extend per-site observation snapshots:

| Column                | SQL Type                                 | Nullable / Default | Notes                                                                                                               |
| --------------------- | ---------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `permitted_equipment` | `JSONB().with_variant(JSON(), "sqlite")` | `nullable=True`    | Preserves `None` for legacy snapshots; stores `list[str]` on new polls                                              |
| `max_vehicle_length`  | `Integer`                                | `nullable=True`    | `CheckConstraint("max_vehicle_length IS NULL OR max_vehicle_length > 0", name="ck_scan_result_max_vehicle_length")` |

### `UserScan` (`user_scans` table)

Extend user-owned scan preferences (excluded from `definition_hash` and `UniqueTarget.hash`):

| Column               | SQL Type  | Nullable / Default                                      | Constraint                                                                                                                |
| -------------------- | --------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `min_rv_length`      | `Integer` | `nullable=True`                                         | `CheckConstraint("min_rv_length IS NULL OR (min_rv_length >= 1 AND min_rv_length <= 200)", name="ck_scan_min_rv_length")` |
| `require_accessible` | `Boolean` | `nullable=False, default=False, server_default=false()` | When true, only sites with `is_accessible IS True` qualify                                                                |

---

## 3. Filtering & Revalidation Rules (`src/camply/db/availability.py`, `src/camply/worker/engine/alerts.py`)

`matches_scan_filters` evaluates all four site preferences uniformly:

1. `not scan.preferred_types or campsite_type in scan.preferred_types`
2. `not scan.require_electric or is_electric is True`
3. `not scan.require_accessible or is_accessible is True`
4. `scan.min_rv_length is None or (max_vehicle_length is not None and max_vehicle_length >= scan.min_rv_length)`
5. `bool(matching_available_dates(available_dates, min_stay_length=scan.min_stay_length or 1, allowed_weekdays=scan.allowed_weekdays))`

**Outbox Notification Metadata**:

- Pending notification snapshots in `NotificationOutbox.payload_json` retain `campsite_type`, `is_electric`, `is_accessible`, `max_vehicle_length`, and `permitted_equipment` (using `.get(...)` safely for pre-migration outbox rows so unmigrated `is_accessible` / `max_vehicle_length` values default to `None` and fail closed only if the scan requires them).

---

## 4. Alembic Migration Strategy

- Single additive migration revising the current head (`2d7ab29d3a46`):
  - Adds `campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length` to `campgrounds` with SQLite-safe batch operations and named check constraint `ck_campground_max_rv_length`.
  - Adds `permitted_equipment`, `max_vehicle_length` to `scan_results` with named check constraint `ck_scan_result_max_vehicle_length`.
  - Adds `min_rv_length`, `require_accessible` to `user_scans` with named check constraint `ck_scan_min_rv_length`.
  - `downgrade()` drops added columns and constraints cleanly without disturbing existing `user_scans`, `scan_results`, or `campgrounds` rows.
