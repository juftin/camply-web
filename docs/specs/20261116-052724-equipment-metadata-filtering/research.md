# Research: Equipment Metadata and Filtering

**Feature**: `20261116-052724-equipment-metadata-filtering`
**Date**: 2026-11-16
**Spec**: [spec.md](spec.md)

## 1. Current State Audit

### Discovery Catalog (`search` table & `BaseProvider`)

- `src/camply/db/models/search.py` already defines `campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, and `max_rv_length`.
- `src/camply/server/routers/search.py` and `Search.search()` already accept `has_electric`, `pets_allowed`, and `min_rv_length`, and serialize `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`, and `campsite_types` in `SearchResultResponse`.
- **Gap 1**: `BaseProvider.search_campground_statement` and `BaseProvider.search_rec_area_statement` (`src/camply/providers/base.py`) omit all seven amenity/RV columns when populating `search`, leaving them at schema defaults (`False` / `None`).
- **Gap 2**: `Campground` (`src/camply/db/models/campgrounds.py`) does not persist normalized capability columns, so `populate_search_table` has no campground-level source to copy or aggregate into `search`.
- **Gap 3**: `/api/v1/search/explore` (and `SearchPage.tsx`) exposes `electric`, `pets`, and `rv`, but does not yet expose an `ada_accessible` query filter despite the column already existing on `Search`.

### Saved Scans & Poller Matching (`user_scans`, `scan_results`, `availability.py`)

- `UserScan` (`src/camply/db/models/user_scans.py`) currently supports `min_stay_length`, `preferred_types`, `require_electric`, and `allowed_weekdays`.
- `ScanResult` (`src/camply/db/models/scan_results.py`) already persists `campsite_type`, `is_electric`, and `is_accessible`, and `CampsiteDTO` carries `is_electric`, `is_accessible`, and provider-specific `metadata`.
- **Gap 4**: `CampsiteDTO` and `ScanResult` have no normalized top-level `max_vehicle_length: int | None` or `permitted_equipment: list[str]` fields.
- **Gap 5**: `UserScan` has no `min_rv_length: int | None` (required vehicle length in whole feet) or `require_accessible: bool` preference, and `matches_scan_filters` (`src/camply/db/availability.py`) does not evaluate length or accessibility.
- **Gap 6**: `alerts.py` (`matching_opening`) and `area_alerts.py` revalidate pending outbox payloads against `matches_scan_filters`; notification metadata snapshots must include `is_accessible`, `max_vehicle_length`, and `permitted_equipment` so revalidation after scan edits matches `matching_scan_results` identically.

---

## 2. Provider Capabilities & Extraction Strategy

### Decision 1: Unified Site Capability Normalization on `CampsiteDTO`

- **Decision**: Add `max_vehicle_length: int | None = None` and `permitted_equipment: list[str] = Field(default_factory=list)` directly to `CampsiteDTO` (and persist `max_vehicle_length` + `permitted_equipment` on `ScanResult`), alongside existing `campsite_type`, `is_electric`, and `is_accessible`.
- **Rationale**: Keeping normalized capabilities on `CampsiteDTO` and `ScanResult` avoids provider-specific parsing inside `db/availability.py` or `worker/`, preserves Constitution Principle IV (clean provider/worker separation), and lets every subscriber sharing a `UniqueTarget` filter independently against cached `ScanResult` rows.
- **Alternatives considered**: Parsing provider-specific `metadata` JSON blobs inside `availability.py` — rejected because every provider uses different keys (`VehicleLength`, `permitted_equipment`, `Attributes`, `max_length`) and `ScanResult` does not currently store `metadata`.

### Decision 2: Provider-by-Provider Extraction Rules

1. **Recreation.gov** (`src/camply/providers/recreation_gov/`):
   - **Site-level (`RecDotGovCampsite`)**: Already fetches `permitted_equipment: list[RecDotGovEquipment]` (`equipment_name`, `max_length: float`), `accessible: bool`, and `attributes` (`AttributeName` / `AttributeValue`).
     - Compute `max_vehicle_length` from `RecDotGovEquipment` entries whose `equipment_name` denotes drivable/towable RV/trailer/vehicle equipment (excluding `"Tent"`-only or `"Small Tent"` entries when checking RV/vehicle length; if `max_length > 0`, floor to positive `int` feet, treating `<= 0` as `None`). Also inspect driveway/pad length attributes when `permitted_equipment` omits RV entries.
   - **Discovery-level (`populate_database` / RIDB)**: The existing `RIDBFullExport_V1_JSON.zip` streamed during `populate_database` contains `Campsites_API_v1.json`, `CampsiteAttributes_API_v1.json`, and `PermittedEquipment_API_v1.json` (or facility attributes in the same archive). Stream those files in `ijson` during `populate_database` to compute per-`FacilityID` aggregate `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`, and `campsite_types` before committing `Campground` and `Search` atomically.
2. **UseDirect (10 deployments)** (`src/camply/providers/usedirect/`):
   - **Site-level (`AvailabilityUnit`)**: Already reads `UnitTypesGroups`, `SleepingUnitIds` -> `permitted_equipment`, `IsAda`, and `VehicleLength: int | None`. Map `VehicleLength` > 0 directly to `max_vehicle_length` (treating `<= 0` or `None` as `None`).
   - **Discovery-level (`populate_database` + optional enrichment)**: UseDirect's `fd/places` and `fd/facilities` omit per-site amenities, while `search/filters` exposes `UnitTypesGroups` / `NightlySleepingUnits` and `usedirect/enrichment.py` already fetches `ParkInformation` (including `TrailerMaxLength` / `RVMaxLength` and park attributes) into `Campground.details`. During `populate_database`, retain/promote any verified capabilities from `Facility` / existing `details.vehicle_limits` or facility park-information endpoints without adding unbounded per-facility HTTP calls to the atomic catalog sync; enrichments that refresh `Campground.details` can also refresh the normalized discovery summary and `Search` row.
3. **GoingToCamp (14 deployments)** (`src/camply/providers/going_to_camp/`):
   - **Site-level (`Resource`)**: Already decodes `allowedEquipment` into `permitted_equipment` (e.g., `"RV/Trailer up to 35ft"`, `"2 Trailers/RVs up to 40ft"`) and `definedAttributes` into `decoded_attributes` (e.g., `"Equipment Length"`, `"Max Vehicle Length"`, `"Electrical Service"`, `"ADA Accessible"`). Extract `max_vehicle_length` conservatively by inspecting numeric length attributes and RV/trailer/vehicle equipment labels (converting metric `"m"` strings conservatively downward to whole feet via `math.floor(meters * 3.28084)` and taking `int` feet from `"ft"`/`"'"` patterns).
   - **Discovery-level**: GoingToCamp catalog sync fetches bulk `transactionlocation`, `resourceLocation`, `bookingcategories`, and `resourcecategory` (it does not fetch per-campground `resourcelocation/resources` across 100+ campgrounds in one sync). `populate_database` populates `campsite_types` from `resourceCategoryIds` + `ResourceCategory` display names where determinable (e.g., cabin/tent/RV), while preserving any verified site-derived or enriched attributes already observed for the campground rather than blocking catalog sync with hundreds of HTTP requests.
4. **ReserveAmerica** (`src/camply/providers/reserve_america/`):
   - **Site-level (`Site`)**: Already receives `details.attributes: list[Attribute]` (`id`, `name`, `value`) on every availability grid response! Extract `max_vehicle_length` from length attributes (such as max vehicle/driveway/RV/trailer length attributes, positive integer feet only) and normalize `permitted_equipment` from equipment/site-type attributes alongside existing `is_electric` (attr `218`) and `is_accessible` (attr `104`).
   - **Discovery-level**: ReserveAmerica's bulk search endpoint (`/search`) and facility detail API (`facilities/{contract}/{facility}` in `reserve_america/enrichment.py`) expose facility attributes (`pets`, `electric`, `water`, `sewer`, `ada`, `max_rv_length` where published); map verified attributes during `populate_database` / enrichment without inventing unverified amenities.

---

## 3. Length & Filter Matching Semantics

### Decision 3: Fail-Closed Filtering & Length Conversion

- **Decision**:
  - User `min_rv_length` is an optional integer in whole feet (`1 <= min_rv_length <= 200`, `None` when unrestricted). Inputs `<= 0` or `> 200` fail Pydantic validation before writes.
  - Matching rule in `matches_scan_filters`:
    - `preferred_types`: existing rule (`not scan.preferred_types or campsite_type in scan.preferred_types`).
    - `require_electric`: existing rule (`not scan.require_electric or is_electric is True`).
    - `require_accessible`: `not scan.require_accessible or is_accessible is True`.
    - `min_rv_length`: `scan.min_rv_length is None or (max_vehicle_length is not None and max_vehicle_length >= scan.min_rv_length)`.
  - Unit conversion: If an upstream provider supplies fractional feet (e.g. `27.5`) or meters (e.g. `8m`), floor conservatively to whole feet (`27` ft / `26` ft) so a site never falsely passes a user's length requirement. If upstream supplies `0` or `<= 0`, normalize to `None` (unknown/not RV-rated).
- **Rationale**: Matches `FR-007`, `FR-009`, `FR-010`, and Constitution Principle I (accuracy over false positives).
- **Alternatives considered**: Allowing `max_vehicle_length is None` to pass `min_rv_length` with a UI warning — rejected because alerting RV campers on tent-only or unknown-pad-length sites causes real booking failures.

### Decision 4: Portable SQLite & PostgreSQL Aggregation for `search_rec_area_statement`

- **Decision**: Compute `RecreationArea` discovery summaries directly in `BaseProvider.search_rec_area_statement` from enabled, reservable child `Campground` rows using portable SQL (`func.max(case((Campground.has_electric.is_(True), 1), else_=0)) == 1`, `func.max(Campground.max_rv_length)`, and unioning `campsite_types` or storing pre-aggregated capabilities cleanly).
- **Rationale**: `camply-web` runs on both SQLite (standalone + tests) and PostgreSQL (distributed). Avoids PostgreSQL-only `BOOL_OR` or `ARRAY_AGG` in `BaseProvider`, keeping both migration and query paths identical. Note: Because SQLite stores `ARRAY(String).with_variant(JSON(), "sqlite")` as JSON arrays, aggregating distinct `campsite_types` per recreation area in Python or via a lightweight query during `populate_search_table` avoids dialect-specific array aggregation SQL completely!
- **Alternatives considered**: Dialect-branched `BOOL_OR` / `json_group_array` SQL — rejected for unnecessary SQLite/Postgres divergence.

### Decision 5: Shared Target Deduplication & Outbox Compatibility

- **Decision**: `min_rv_length` and `require_accessible` live on `UserScan` only and MUST NOT be included in `UniqueTarget` hash or `UserScan.definition_hash`? Wait: check `definition_hash`!
  - Let's verify: `UserScan.definition_hash` deduplicates identical scan _definitions_ per user (`provider_id`, `destination_type`, `destination_id`, `start_date`, `end_date`, `coverage_mode`, `selected_ids`). Preferences (`min_stay_length`, `preferred_types`, `require_electric`, `allowed_weekdays`) are NOT in `definition_hash` or `UniqueTarget.hash`! Keeping `min_rv_length` and `require_accessible` in the same preference bucket preserves one `UniqueTarget` per `(provider_id, campground_id, start_date, end_date)` across all subscribers.
- **Backward Compatibility**: All new `UserScan`, `ScanResult`, and `Campground` columns are nullable or have safe defaults (`require_accessible = False`, `min_rv_length = None`, `max_vehicle_length = None`, `permitted_equipment = None`). Existing `ScanResult` rows without `max_vehicle_length` continue working for unrestricted scans and fail closed for strict length scans until the next poll refreshes the row.
