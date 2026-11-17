# Research: CLI Full-Stack Parity

**Feature**: `031-cli-fullstack-parity`
**Date**: 2026-11-16
**Spec**: [spec.md](spec.md)

## 1. Existing Codebase Audit

### CLI Architecture & Import Boundaries (`src/camply/cli/`, `pyproject.toml`)

- `src/camply/cli/main.py` defines `CamplyCLI`, a lazy `click.Group` that resolves `serve`, `db`, `providers`, `recreation-areas`, `campgrounds`, and `campsites` on demand so unrelated command groups do not import each other's dependencies.
- `pyproject.toml` enforces two critical Import Linter contracts on `camply.cli` and `camply.core`:
  1. **Component dependency layers**: `cli | server | worker` → `core` → `notifications | providers` → `db` → `__about__`.
  2. **Base dependencies stay optional-free**: `camply.cli.**`, `camply.core.**`, `camply.notifications.**`, `camply.providers.**`, and `camply.db.**` cannot import `fastapi`, `uvicorn`, `gunicorn`, `orjson`, `jwt`, `cryptography`, `prometheus_client`, `celery`, `redis`, `psycopg`, or `sentry_sdk`.
- **Implication**: Because `camply.notifications` (`PushoverProvider`, `NtfyProvider`, `NotificationDTO`) and `camply.db.notification_config` (`validate_ntfy_url`) already reside in lower base-only layers, `camply.cli` and `camply.core` can import them directly without violating any Import Linter contract or requiring `server`/`distributed` extras.

### Foreground Availability & Filtering (`src/camply/core/search.py`, `src/camply/db/availability.py`)

- `CampsiteDTO` (`src/camply/providers/dto.py`) already normalizes `campsite_id`, `campsite_name`, `campsite_type` (`TENT`, `RV`, `CABIN`, `OTHER`), `is_electric`, `is_accessible`, `permitted_equipment`, and `max_vehicle_length` across all 26 providers (completed in [feature 030](../030-equipment-metadata-filtering/spec.md)).
- `PROVIDERS` and `get_provider_filter_capabilities` (`src/camply/providers/__init__.py`) already expose `ProviderFilterCapabilities(preferred_types, require_electric, require_accessible, min_rv_length)` per provider class.
- **Gap**: `camply.core.search.SearchRequest` and `_stays()` currently only filter by date windows, weekday nights, and exact stay length (`nights`), ignoring `campsite_type`, `is_electric`, `is_accessible`, `max_vehicle_length`, and `--campsite` ID/name selectors.

### Notifications (`src/camply/notifications/`)

- `PushoverProvider` (`src/camply/notifications/pushover.py`) and `NtfyProvider` (`src/camply/notifications/ntfy.py`) implement async `send_accepted(...) -> bool` using `httpx2` and `jiter` (both in base dependencies).
- **Gap**: The CLI has no `--notifications` option, no `test-notifications` command, and no seen-opening deduplication tracker (in-memory or file-backed) for foreground or single-pass CLI runs.

### Discovery & Database Metadata (`src/camply/cli/discovery.py`, `src/camply/cli/db.py`)

- `BaseProvider.search()` and `ProviderSearchQuery` (`src/camply/providers/dto.py`) already validate `limit: int = Field(default=50, ge=1, le=1000, strict=True)`, while `src/camply/cli/discovery.py` hardcodes `DISPLAY_LIMIT = 50` and `RESULT_PROBE = DISPLAY_LIMIT + 1`.
- `camply db metadata` (`src/camply/cli/db.py`) currently only accepts numeric `--provider-id` (`1`–`26` or `all`), whereas `camply.cli.providers.provider_entries()` maps canonical CLI names (`RecreationDotGov`, `ReserveCalifornia`, etc.) and class names to provider IDs.

---

## 2. Technical Decisions

### Decision 1: Shared Site-Attribute & Campsite-ID Filtering in `camply.core.search`

- **Decision**: Extend `SearchRequest` in `src/camply/core/search.py` with optional filter fields (`campsites`, `campsite_types`, `require_electric`, `require_accessible`, `min_rv_length`) and evaluate them in `_stays()` before constructing sliding stays, using the exact same boolean predicates as `camply.db.availability.matches_scan_filters`:
  - `campsite_types`: site's `campsite_type.value` is in `request.campsite_types` (when non-empty).
  - `require_electric`: `site.is_electric is True`.
  - `require_accessible`: `site.is_accessible is True` (unknown/false fails closed).
  - `min_rv_length`: `site.max_vehicle_length is not None and site.max_vehicle_length >= request.min_rv_length` (unknown/`None` fails closed).
  - `campsites`: `site.campsite_id.strip()` matches an exact selector OR `site.campsite_name.strip().casefold()` matches a casefolded selector (when non-empty).
- **Rationale**: Keeps CLI and web availability filtering 100% consistent without requiring a database `UserScan` ORM instance during stateless CLI runs.
- **Alternatives considered**: Constructing a transient `UserScan` ORM model in `camply.core.search` and calling `matches_scan_filters` — rejected because `core` should stay lightweight and decoupled from SQLAlchemy ORM instantiation for stateless CLI invocations.

### Decision 2: Upfront Provider Filter Capability Validation & Display

- **Decision**: Validate requested site-attribute filters (`--campsite-type`, `--electric`, `--accessible`, `--rv-length`) against `provider_class.filter_capabilities` in `campsites_cmd` before resolving targets or making HTTP requests. Update `render_providers` in `src/camply/cli/output.py` to list supported site filters alongside discovery and availability capabilities.
- **Rationale**: Matches `/api/scans` validation (`_validate_provider_filter_support` in `src/camply/server/routers/scans.py`) and satisfies `FR-001`, `FR-002`, and `SC-002`.
- **Alternatives considered**: Warning and ignoring unsupported filters — rejected by specification edge cases and `SC-002`.

### Decision 3: Stateless CLI Notification Resolution & Delivery

- **Decision**: Introduce `src/camply/cli/notifications.py` to handle:
  1. Credential/config resolution from `--notifications` (`pushover`, `ntfy`), `--ntfy-topic`, `--ntfy-server`, and environment variables (`PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`, `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_ACCESS_TOKEN`).
  2. Validation before polling:
     - When `--notifications` is omitted, zero notification environment variables are read or validated.
     - When `pushover` is selected, both `PUSHOVER_USER_KEY` and `PUSHOVER_APP_TOKEN` must be non-blank.
     - When `ntfy` is selected, a valid topic (`^[A-Za-z0-9_-]{1,64}$`) and HTTP(S) server URL (`validate_ntfy_url`, defaulting to `https://ntfy.sh`) are required, and any `NTFY_ACCESS_TOKEN` must be printable ASCII.
  3. Delivery via existing `PushoverProvider(client)` and `NtfyProvider(client)` in `src/camply/notifications/`.
  4. `camply test-notifications` command registered lazily in `CamplyCLI`: requires at least one `--notifications` channel, sends a test `NotificationDTO` via `send_accepted`, and raises `click.ClickException` (exit code 1) if any selected channel fails or rejects the message.
- **Rationale**: Reuses existing base-package notification providers, keeps secret tokens out of shell process arguments/history, and satisfies `FR-003` and `FR-008`.
- **Alternatives considered**: Reading credentials from `.camply` YAML files or database `User` rows — rejected during `/speckit-clarify` (`Q2`).

### Decision 4: Seen-Opening Deduplication & Optional State File

- **Decision**: Identify each qualifying stay by a canonical string key `"{provider_id}:{campground_id}:{campsite_id}:{arrival.isoformat()}:{checkout.isoformat()}"`.
  - During `monitor()` (or a single check when `--state-file` is provided), maintain `seen_keys: set[str]`.
  - On each successful `check_availability()` cycle:
    - Compute `current_keys = {stay_key(stay) for stay in stays}`.
    - Filter `new_stays = [stay for stay in stays if stay_key(stay) not in seen_keys]`.
    - Replace `seen_keys = current_keys` (and atomically write sorted keys as JSON to `--state-file` when configured).
    - Dispatch external notifications only for `new_stays`. Transient notification delivery errors are logged as sanitized warnings on stderr without aborting the watch loop.
  - If `check_availability()` raises an upstream provider error, `seen_keys` and the state file remain untouched so previously open stays are not falsely treated as closed and reopened on recovery.
- **Rationale**: Satisfies `FR-004` and `SC-003` for both continuous loops and cron-driven `--search-once --state-file` invocations without requiring SQLite/PostgreSQL.
- **Alternatives considered**: Persisting state in the application SQLite database — rejected to keep `camply campsites` 100% database-free (`Q4`).

### Decision 5: Run-Mode Controls (`--search-once`, `--interval`) & Discovery Limit (`--limit`)

- **Decision**:
  - Add `--search-once` (`is_flag=True`, default `False`) and `--interval` (`click.FloatRange(min=5.0)`, default `60.0`) to `camply campsites`. When `--search-once` is set, `campsites` executes one `check_availability()` cycle, renders output, sends any configured notifications, saves `--state-file` if set, and exits cleanly (`0`).
  - Add `--limit` (`click.IntRange(min=1, max=500)`, default `50`) to `camply recreation-areas` and `camply campgrounds`. Request `limit + 1` from `BaseProvider.search(..., limit=limit + 1)` (well within `ProviderSearchQuery`'s `le=1000` ceiling) to preserve accurate truncation warnings when more than `--limit` results exist.
- **Rationale**: Satisfies `FR-005` and `FR-006` while protecting upstream providers from sub-5-second polling and preserving existing truncation detection.

### Decision 6: Structured JSON Output (`--json`) & Stream Separation

- **Decision**: Add `--json` (`is_flag=True`, default `False`) to `providers`, `recreation-areas`, `campgrounds`, and `campsites`.
  - On `campsites`, `--json` requires `--search-once` (if `--json` is passed without `--search-once`, raise `click.UsageError("--json requires --search-once on campsites.")` so stdout always receives a single valid JSON array/document).
  - When `--json` is active, `set_up_logging` routes all log records (including `INFO` and `CAMPLY`) to `stderr` so `stdout` contains exclusively the serialized JSON payload.
- **Rationale**: Satisfies `FR-007` and ensures `camply ... --json | jq` works cleanly even when warnings or debug logs are emitted.
