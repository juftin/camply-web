# Data Model: CLI Full-Stack Parity

**Feature**: `031-cli-fullstack-parity`
**Date**: 2026-11-16
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

_Note: All user-facing CLI enhancements in this specification are stateless and require **zero database schema changes or Alembic migrations**._

## 1. Core Search Models (`src/camply/core/search.py`)

### `SearchRequest` (extended)

Frozen Pydantic v2 model representing a validated local CLI availability query:

| Field                | Type                       | Default      | Validation & Semantics                                                                                  |
| -------------------- | -------------------------- | ------------ | ------------------------------------------------------------------------------------------------------- |
| `windows`            | `tuple[DateWindow, ...]`   | _(required)_ | Merged contiguous arrival/checkout date intervals                                                       |
| `eligible_dates`     | `frozenset[date]`          | _(required)_ | Unexpired booking nights matching windows and weekday filters                                           |
| `nights`             | `int`                      | `1`          | Exact consecutive nights per stay (`ge=1`)                                                              |
| `campsites`          | `tuple[str, ...]`          | `()`         | Trimmed non-blank campsite IDs or case-insensitive site names (requires `--campground` or `--rec-area`) |
| `campsite_types`     | `tuple[CampsiteType, ...]` | `()`         | Allowed standardized site types (`TENT`, `RV`, `CABIN`, `OTHER`); empty means all types                 |
| `require_electric`   | `bool`                     | `False`      | When `True`, only sites with `is_electric is True` match                                                |
| `require_accessible` | `bool`                     | `False`      | When `True`, only sites with `is_accessible is True` match                                              |
| `min_rv_length`      | `int \| None`              | `None`       | Optional minimum vehicle/RV length in whole feet (`ge=1, le=200`); `None` means unrestricted            |
| `warnings`           | `tuple[str, ...]`          | `()`         | Past-start clamping warnings                                                                            |

**Site-Matching Predicate (`site_matches_request`)**:

For each observed `CampsiteDTO` in `_stays()`:

1. **Campsite selector**: `not request.campsites or site.campsite_id.strip() in request.campsites or site.campsite_name.strip().casefold() in {c.casefold() for c in request.campsites}`
2. **Campsite type**: `not request.campsite_types or site.campsite_type in request.campsite_types`
3. **Electric hookup**: `not request.require_electric or site.is_electric is True`
4. **ADA accessibility**: `not request.require_accessible or site.is_accessible is True`
5. **Minimum RV length**: `request.min_rv_length is None or (site.max_vehicle_length is not None and site.max_vehicle_length >= request.min_rv_length)`

---

## 2. CLI Notification Models (`src/camply/cli/notifications.py`)

### `CLINotificationConfig`

Frozen Pydantic v2 model validated before any availability polling or test notification begins:

| Field                | Type                                      | Default             | Source & Validation                                                                                              |
| -------------------- | ----------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `channels`           | `tuple[Literal["pushover", "ntfy"], ...]` | `()`                | Deduplicated lowercase values from repeatable `--notifications`                                                  |
| `pushover_user_key`  | `str \| None`                             | `None`              | From `PUSHOVER_USER_KEY` env var; required when `"pushover"` in `channels` (`repr=False`)                        |
| `pushover_app_token` | `str \| None`                             | `None`              | From `PUSHOVER_APP_TOKEN` env var; required when `"pushover"` in `channels` (`repr=False`)                       |
| `ntfy_topic`         | `str \| None`                             | `None`              | From `--ntfy-topic` flag or `NTFY_TOPIC` env var; required when `"ntfy"` in `channels` (`^[A-Za-z0-9_-]{1,64}$`) |
| `ntfy_server_url`    | `str`                                     | `"https://ntfy.sh"` | From `--ntfy-server` flag or `NTFY_SERVER_URL` env var; validated via `validate_ntfy_url`                        |
| `ntfy_access_token`  | `str \| None`                             | `None`              | From `NTFY_ACCESS_TOKEN` env var; printable ASCII if set (`repr=False`)                                          |

### `StayDeduplicationState`

Tracks seen qualifying stays across poll cycles and optional `--state-file` JSON persistence:

- **Canonical Stay Key**: `f"{stay.campground.provider_id}:{stay.campground.campground_id}:{stay.campsite_id}:{stay.arrival.isoformat()}:{stay.checkout.isoformat()}"`
- **State File JSON Schema** (when `--state-file PATH` is supplied):
  ```json
  {
    "version": 1,
    "seen_stays": ["1:232450:99001:2027-07-10:2027-07-13"]
  }
  ```
- **Lifecycle**:
  1. **Initialize**: Empty set `{}` in memory, or loaded from `--state-file` if the file exists (raising a clear `ClickException` or warning without crashing console output if the file is unreadable/corrupted).
  2. **Evaluate on successful check**:
     - `new_stays = [stay for stay in stays if stay_key(stay) not in seen_stays]`
     - Update `seen_stays = {stay_key(stay) for stay in stays}` and write atomically to `--state-file` (if configured).
  3. **Preserve on provider error**: If `check_availability` raises an exception, `seen_stays` and `--state-file` are untouched.

---

## 3. JSON Output Payloads (`src/camply/cli/output.py`)

When `--json` is passed, `stdout` emits a single UTF-8 JSON document:

- **`camply providers --json`**: List of objects with `name`, `display_name`, `provider_id`, `url`, `recreation_area_discovery`, and `filter_capabilities` (`preferred_types`, `require_electric`, `require_accessible`, `min_rv_length`).
- **`camply recreation-areas --json` / `camply campgrounds --json`**: List of serialized `ProviderSearchResult` objects (`entity_type`, `provider_id`, `provider_name`, `recreation_area_id`, `recreation_area_name`, `campground_id`, `campground_name`, `city`, `state`, `country`, `latitude`, `longitude`, `booking_url`).
- **`camply campsites --search-once --json`**: List of serialized stay objects (`provider_id`, `provider_name`, `recreation_area_id`, `recreation_area_name`, `campground_id`, `campground_name`, `campsite_id`, `campsite_name`, `arrival`, `checkout`, `nights`, `booking_url`).
