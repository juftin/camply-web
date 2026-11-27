# HTTP contract: Area and selected-campground scans

Proposed extensions to existing `/api` routes. Current authentication, password, invitation, ownership, administrator and CSRF rules remain in effect. Public metadata stays public. No implementation or OpenAPI regeneration occurs in this change.

## Create and update

`POST /api/scans` retains dates and preferences. Add these explicit destination variants:

| Variant                          | Required destination fields                                                                                                  | Forbidden non-null fields                               |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Campground (also legacy default) | `provider_id`, `campground_id`; `destination_type` omitted or `campground`                                                   | `recreation_area_id`, `coverage_mode`, `campground_ids` |
| Whole area                       | `provider_id`, `destination_type=recreation_area`, `recreation_area_id`, `coverage_mode=all`                                 | `campground_id`, `campground_ids`                       |
| Selected area campgrounds        | `provider_id`, `destination_type=recreation_area`, `recreation_area_id`, `coverage_mode=selected`, nonempty `campground_ids` | `campground_id`                                         |

IDs are opaque nonempty strings of at most 128 characters; trim outer whitespace but preserve native identity. Deduplicate and sort selections before comparison. An explicit null is treated as absent only for destination fields irrelevant to the chosen variant; required fields cannot be null. Existing preference defaults stay unchanged. Check-out must follow check-in, and minimum stay must be positive and no longer than the date window.

Example selected-area request (synthetic identifiers):

```json
{
  "destination_type": "recreation_area",
  "provider_id": 1,
  "recreation_area_id": "area-demo",
  "coverage_mode": "selected",
  "campground_ids": ["camp-a", "camp-c"],
  "start_date": "2027-06-10",
  "end_date": "2027-06-14",
  "min_stay_length": 2,
  "preferred_types": ["TENT"],
  "require_electric": false
}
```

Creation returns `201`. One transaction validates the full choice, checks canonical duplicate identity, gets/creates shared targets, creates the saved definition and coverage links. Concurrent identical creates return one success and one `409`, never duplicate subscriptions.

`PATCH /api/scans/{id}` preserves the scan UUID/creation time and merges omitted dates/preferences. Preserve legacy campground patches, including campground/provider replacement with the existing merged validation. For an area or a change of destination kind, supplying a destination identity requires a complete new destination variant. Changing area/provider cannot inherit the old selection. Changing only mode to `selected` requires `campground_ids`; changing only mode to `all` clears saved choices. Updating `campground_ids` without a mode is valid only for a scan already in selected mode. Explicit nulls do not clear dates/preferences. Existing unavailable choices may be retained only when they already belong to the same saved area definition; newly supplied choices must be eligible. Changing destination/coverage requires at least one eligible member; date/filter-only edits on unavailable saved scans remain permitted.

Concurrent edits use internal row-version compare-and-swap. A stale write returns `409` with conflict kind `scan_changed` and instructions to reload; it cannot overwrite a newer saved selection. No new public version parameter is required. Pausing/resuming continues to use `is_active`; suspended users may edit or pause but cannot resume. Delete returns `204`, removes only this scan's links, and invalidates pending delivery for it.

## Errors

| Status        | Meaning                                                                                                                                              |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `401` / `403` | Existing authentication/access/CSRF restrictions.                                                                                                    |
| `404`         | Unknown destination, missing scan, or foreign-owned scan.                                                                                            |
| `409`         | Duplicate normalized scan definition (`duplicate_scan`) or concurrent edit (`scan_changed`).                                                         |
| `422`         | Conflicting shape, blank IDs, invalid dates/stay, empty selection, ineligible destination, or any invalid/cross-area/cross-provider selected member. |

Use the existing error envelope, with actionable text. Selection validation is all-or-nothing. No provider availability request occurs during create/update; catalog validation uses confirmed stored membership.

## Eligible campground choices

Add `GET /api/rec-area/{provider}/{id}/monitoring-campgrounds` without changing the original `/campgrounds` metadata array.

Parameters: `query` (default empty, trimmed, case-insensitive campground-name substring), `limit` (default 50, range 1–100), `offset` (default 0, nonnegative). Order by normalized campground name, then exact ID. Return:

- `items`: eligible members with `id`, `provider_id`, `recreation_area_id`, `name`, and nullable state/city.
- `total`: count matching this query before pagination.
- `eligible_total`: count of all eligible members in this area, independent of query/page.
- `limit`, `offset`, `has_more`, `catalog_revision`: pagination and confirmed-publication identity.

Unknown area returns `404`. Disabled area returns `422` with an unavailable explanation. A known enabled area with no eligible children returns an empty success. All-mode expansion uses the full catalog predicate, never this route's page limit. Selection discovery may span catalog revisions; keep saved draft selections and revalidate the whole submission rather than silently dropping choices.

## Scan representations

Keep the existing list envelope, pagination and filters. Campground scans retain real `campground_id`, name, dates/preferences, and `last_checked_at` behavior. Add these fields to user and corresponding admin scan representations:

| Field                                                                                   | Contract                                                                                                                                                                   |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `destination_type`, `destination_name`                                                  | Explicit kind and last known label.                                                                                                                                        |
| `recreation_area_id`, `recreation_area_name`                                            | Area identity/context; campground context remains available.                                                                                                               |
| `campground_id`, `campground_name`                                                      | Actual campground values for campground scans; null for area scans.                                                                                                        |
| `coverage_mode`                                                                         | `all`/`selected` for areas, null for campground scans.                                                                                                                     |
| `campground_ids`                                                                        | Complete normalized fixed selection for selected mode; empty otherwise.                                                                                                    |
| `eligible_campground_count`, `unavailable_selection_count`, `matching_campground_count` | Separate eligible coverage, saved unavailable selection, and matching-result counts.                                                                                       |
| `destination_available`                                                                 | False for removed/disabled parent; independent of saved active preference.                                                                                                 |
| `coverage_status`                                                                       | `waiting`, `checking`, `partial`, `complete`, or `no_eligible_campgrounds`. Destination availability, active preference and ended dates are independent status dimensions. |
| `checked_campground_count`, `failed_campground_count`, `pending_campground_count`       | Current round: successful, terminal-failed, or unresolved members; sum equals captured eligible count. A retrying member remains pending but carries its latest error.     |
| `last_full_checked_at`                                                                  | Area full success for current coverage, null until established. Area legacy `last_checked_at` aliases this full-check time, never one child timestamp.                     |

`GET /api/scans/{id}` additionally returns `campgrounds`: full saved selection or all current coverage, with provider/campground ID, last known name, eligibility/unavailable reason, nullable target UUID, round outcome, last successful check, latest attempt and sanitized error category. Fixed unavailable selections remain present. Results remain available if destination metadata cannot be loaded. Matching counts expire dates and apply preferences identically to alerts.

Each result adds `provider_id`, `campground_id`, `campground_name`, `last_checked_at`, and `is_stale`, while retaining existing site fields, dates/attributes and booking URL. Distinct identity is `(provider_id, campground_id, campsite_id)`; grouping stays happens inside that identity before union across targets. The current result response remains a complete filtered set; existing client-side bounded stay-group display/search is retained, without adding a second results pagination protocol.

An area may be complete but stale between rounds; timestamps convey observation age. A failure retains old results with `is_stale=true`. While retries/pending checks remain, coverage is partial/checking; zero qualifying results cannot imply every campground has been checked successfully. Paused and ended display behavior overrides active presentation without altering coverage outcome data.

## Administration and compatibility

Admin scan list/detail/user scan summaries expose one row per saved scan, with the same destination/coverage identity. Legacy admin `target_id` is a real UUID for campground scans and null for area scans. Area details expose their actual member target links through `campgrounds`.

`GET /api/admin/targets/{id}` stays campground-level. Count/list linked saved scans once through the association, not one row per join or distinct users. Active/overdue/dormant target classification uses association-aware eligible coverage. Overview counts distinguish saved scans from shared targets; existing audit actions retain their ownership/suspension semantics.

Generated OpenAPI and handwritten frontend scan interfaces must be updated together during implementation. This is additive for legacy campground writes and scalar campground responses; clients wishing to display newly introduced area scans must handle explicit destination type and nullable campground/target fields. A matched frontend/backend release is required.
