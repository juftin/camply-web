# Filtering & Metadata Quality Checklist: Equipment Metadata and Filtering

**Purpose**: Verify specification and plan completeness across provider metadata, filtering semantics, migrations, and UI contracts before task execution
**Created**: 2026-11-16
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md)

## Discovery Metadata & Aggregation (`T3.2.1b`)

- [x] All seven discovery capability fields (`campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`) have explicit population rules on `Campground` and `Search`
- [x] Parent `RecreationArea` aggregation rules include only enabled, reservable child campgrounds and use dialect-portable logic for SQLite and PostgreSQL
- [x] Unverified provider attributes default conservatively rather than inferring electricity from water/sewer or inventing missing facets
- [x] Explore ADA accessibility filter parity is specified across list and map endpoints

## Equipment Length & Accessibility Filtering (`T3.2.2`)

- [x] Unit semantics are unambiguous (whole feet; fractional/metric provider values floored conservatively; `0`/negative provider values normalized to unknown)
- [x] Fail-closed rules are explicit for both `min_rv_length` and `require_accessible` when site capability metadata is `None` / unknown
- [x] Input validation bounds (`1 <= min_rv_length <= 200`, `None` for unrestricted, `<= 0` rejected) and `PATCH` omission vs `null` clear semantics are defined
- [x] Shared-target deduplication (`UniqueTarget.hash` and `UserScan.definition_hash` unchanged) is preserved across subscribers with different equipment preferences
- [x] Pending outbox notifications (`alerts.py`, `area_alerts.py`) revalidate against updated `min_rv_length` and `require_accessible` preferences

## Provider Family Coverage & Resilience

- [x] Extraction sources and fallback behavior are documented for all four provider families (`RecreationGovProvider`, `UseDirectProvider`, `GoingToCampProvider`, `ReserveAmericaProvider`)
- [x] Optional enrichment/detail failures never abort atomic catalog ingestion or existing availability polling
- [x] Existing saved scans and pre-migration `ScanResult` / outbox rows upgrade without losing data or inventing restrictions
