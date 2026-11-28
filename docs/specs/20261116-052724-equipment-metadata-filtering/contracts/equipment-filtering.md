# Interface Contracts: Equipment Metadata and Filtering

**Feature**: `20261116-052724-equipment-metadata-filtering`
**Date**: 2026-11-16

## 1. Explore Discovery API (`src/camply/server/routers/search.py`)

### `GET /api/v1/search/explore` & `GET /api/v1/search/explore/map` & `GET /api/v1/search/explore/map/group`

Add optional query parameter consistent with `has_electric` and `pets_allowed`:

| Parameter        | Type           | Default | Description                                                                                                                                      |
| ---------------- | -------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ada_accessible` | `bool \| None` | `None`  | When `true`, restrict results to destinations with verified ADA-accessible sites (`false` restricts to unverified/non-ADA, `null` omits filter). |

Existing parameters retained unchanged:

- `has_electric: bool | None = None`
- `pets_allowed: bool | None = None`
- `min_rv_length: int | None = None`

`SearchResultResponse` continues returning `campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, and `max_rv_length`, now populated from provider catalogs.

---

## 2. Scans API (`src/camply/server/schemas.py`, `src/camply/server/routers/scans.py`)

### `ScanCreateRequest`

| Field                | Type          | Default | Validation                                               |
| -------------------- | ------------- | ------- | -------------------------------------------------------- |
| `min_rv_length`      | `int \| None` | `None`  | `ge=1, le=200` when provided (`None` means unrestricted) |
| `require_accessible` | `bool`        | `False` | Require ADA-accessible sites                             |

### `ScanUpdateRequest` (`PATCH /api/v1/scans/{scan_id}`)

| Field                | Type           | Semantics                                                                                                                                 |
| -------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `min_rv_length`      | `int \| None`  | Omitted preserves existing value; `null` clears to unrestricted; integer `1..200` sets requirement (rejects `<= 0` or `> 200` with `422`) |
| `require_accessible` | `bool \| None` | Omitted preserves existing value; boolean updates requirement                                                                             |

_(Note: Verify `ScanUpdateRequest` distinguishes omitted vs explicit `None` via `model_fields_set` so editing dates/status never accidentally clears `min_rv_length`, matching `allowed_weekdays` semantics.)_

### `ScanResponse` / `ScanDetailResponse`

- `min_rv_length: int | None = None`
- `require_accessible: bool = False`

### `ScanResultItem`

| Field                 | Type          | Default | Description                                                            |
| --------------------- | ------------- | ------- | ---------------------------------------------------------------------- |
| `permitted_equipment` | `list[str]`   | `[]`    | Normalized equipment labels allowed at this site (empty if unknown)    |
| `max_vehicle_length`  | `int \| None` | `None`  | Maximum compatible vehicle/RV length in whole feet (`None` if unknown) |

Existing `campsite_type: str | None`, `is_electric: bool | None`, and `is_accessible: bool | None` remain unchanged.

---

## 3. OpenAPI & TypeScript Client Contract

- Regenerate `src/frontend/lib/api/generated/schema.ts` via `task api:generate` after schema updates.
- Verify no drift via `task api:check`.
- Update frontend wrappers in `src/frontend/lib/structs.ts` and `src/frontend/lib/api.ts`:
  - Explore search hooks/URL params (`ada` query param in `SearchPage.tsx` synced with `ada_accessible`).
  - Scan form (`ScanForm.tsx`): numeric optional RV/trailer length input (`1–200` ft, blank = unrestricted) and ADA-accessible toggle, preserved across create/edit/retry/cancel flows.
  - Scan cards/detail/results (`ScanCard.tsx`, `ScanDetail.tsx`, `FoundCampsites.tsx`): preference badges for RV length and ADA requirement, plus site capability badges/text (`Up to {N} ft`, permitted equipment labels, electric, accessible) on matched campsite rows.
