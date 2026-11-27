# Tasks: Equipment Metadata and Filtering

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts](contracts/equipment-filtering.md), [quickstart.md](quickstart.md).

**Tests**: Required by the specification and constitution. Write the relevant behavioral regression first and observe its failure before implementing each slice. Use only synthetic provider and delivery data. Existing `task` wrappers remain the command entrypoints.

**Format**: `- [ ] T### [P?] [US#?] Description with file paths`. `[P]` marks independent files after prerequisites; `[US#]` maps user-story tasks to [spec.md](spec.md).

---

## Phase 1: Setup

- [x] T001 Record baseline tool versions and pre-edit `task lint`, `task check`, `task api:check`, and `task test` status in `docs/specs/20261116-052724-equipment-metadata-filtering/quickstart.md`.
- [x] T002 Add synthetic multi-provider equipment, length (feet, meters, zero/negative sentinels), amenity, and accessibility fixtures in `tests/conftest.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared DTOs, length normalization helpers, database columns, and Alembic migration required before all user stories.

- [x] T003 [P] Add failing unit tests for conservative vehicle-length parsing/flooring (`int` feet > 0, `0`/negative/`None` -> `None`, metric-to-feet flooring) and `CampsiteDTO` capability normalization in `tests/providers/test_base_provider.py`.
- [x] T004 [P] Add failing SQLite/PostgreSQL schema, constraint (`ck_campground_max_rv_length`, `ck_scan_result_max_vehicle_length`, `ck_scan_min_rv_length` checking `1..200`), and populated migration round-trip regressions in `tests/db/test_equipment_migration.py`.
- [x] T005 Add shared positive-length parsing, metric-to-feet flooring, and equipment-label normalization helpers in `src/camply/providers/utils.py`, and add `permitted_equipment: list[str] = Field(default_factory=list)` and `max_vehicle_length: int | None = None` to `CampsiteDTO` in `src/camply/providers/dto.py`.
- [x] T006 Extend `src/camply/db/models/campgrounds.py` with `campsite_types` (`ARRAY(String).with_variant(JSON(), "sqlite")`, `nullable=True`), `has_electric`/`has_water`/`has_sewer`/`pets_allowed`/`ada_accessible` (`Boolean`, `nullable=False, default=False`), and `max_rv_length` (`Integer`, `nullable=True`, `CheckConstraint("max_rv_length IS NULL OR max_rv_length > 0", name="ck_campground_max_rv_length")`).
- [x] T007 Extend `src/camply/db/models/scan_results.py` with `permitted_equipment` (`JSONB().with_variant(JSON(), "sqlite")`, `nullable=True`) and `max_vehicle_length` (`Integer`, `nullable=True`, `CheckConstraint("max_vehicle_length IS NULL OR max_vehicle_length > 0", name="ck_scan_result_max_vehicle_length")`), and extend `src/camply/db/models/user_scans.py` with `min_rv_length` (`Integer`, `nullable=True`, `CheckConstraint("min_rv_length IS NULL OR (min_rv_length >= 1 AND min_rv_length <= 200)", name="ck_scan_min_rv_length")`) and `require_accessible` (`Boolean`, `nullable=False, default=False`); cover exact constraints in `tests/db/test_models.py`.
- [x] T008 Generate and review an additive Alembic migration under `src/camply/db/migrations/versions/` revising `2d7ab29d3a46` via `task backend:migration`, using SQLite-safe batch operations, safe defaults preserving existing rows, and clean downgrade; update `tests/db/test_migration.py`, `tests/db/test_ntfy_migration.py`, `tests/db/test_standalone_database.py`, `tests/db/test_user_session_migration.py`, and `tests/db/test_postgres_migrations.py`.

**Checkpoint**: Foundation schema, DTOs, and portable migration pass before story implementation begins.

---

## Phase 3: US1 — Discover campgrounds by real amenities and RV capacity (P1, MVP)

**Goal**: Populate discovery amenity and RV capacity metadata from provider catalogs and enrichment, aggregate onto recreation areas, and expose ADA filter parity in Explore.

**Independent Test**: Sync synthetic catalogs across all four provider families, verify campground and aggregated recreation-area rows in `search`, and query Explore list/map endpoints with `has_electric`, `pets_allowed`, `ada_accessible`, and `min_rv_length`.

- [x] T009 [P] [US1] Add failing `populate_search_table` and parent `RecreationArea` aggregation tests (enabled/reservable child filtering, SQLite/PostgreSQL portability, conservative unknown defaults) in `tests/db/test_search_model.py`.
- [x] T010 [P] [US1] Add failing Explore `ada_accessible` list/map/group filter and facet regressions in `tests/server/routers/test_search.py` and `tests/db/test_search_maps.py`.
- [x] T011 [P] [US1] Add failing catalog ingestion regressions for discovery amenities (`has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`, `campsite_types`) in `tests/providers/test_recreation_gov.py`, `tests/providers/test_usedirect.py`, `tests/providers/test_going_to_camp.py`, and `tests/providers/test_reserve_america.py`.
- [x] T012 [US1] Update `BaseProvider.search_campground_statement`, `search_rec_area_statement`, and `populate_search_table` in `src/camply/providers/base.py` to copy `Campground` capability columns and aggregate enabled/reservable child capabilities (including unioned `campsite_types` and `MAX(max_rv_length)`) onto `RecreationArea` search rows.
- [x] T013 [US1] Stream RIDB campsite/attribute/permitted-equipment metadata in `src/camply/providers/recreation_gov/provider.py` (and `models/campgrounds.py`) to populate `Campground` discovery capabilities atomically without inferring electricity from water/sewer.
- [x] T014 [P] [US1] Populate verifiable `Campground` discovery capabilities in `src/camply/providers/usedirect/` (`provider.py` + `enrichment.py`), `src/camply/providers/going_to_camp/` (`provider.py`), and `src/camply/providers/reserve_america/` (`provider.py` + `enrichment.py`) while preserving verified attributes across catalog refreshes and failing gracefully on unavailable optional details.
- [x] T015 [US1] Add `ada_accessible: bool | None = None` filter support to `Search.search()` in `src/camply/db/models/search.py` and expose `ada_accessible` on `/api/v1/search/explore`, `/explore/map`, and `/explore/map/group` in `src/camply/server/routers/search.py`.
- [x] T016 [US1] Regenerate `src/frontend/lib/api/generated/schema.ts` via `task api:generate`, wire `ada` URL/query state in `src/frontend/lib/api.ts` and `src/frontend/pages/SearchPage.tsx`, and add regressions first in `src/frontend/pages/SearchPage.test.tsx`.

**Checkpoint**: Explore amenity, ADA, and RV length filters return accurate provider-backed results across list and map views.

---

## Phase 4: US2 — Filter saved scans and alerts by equipment type and vehicle length (P1)

**Goal**: Let campers specify required RV/trailer length (`1..200` ft) on saved scans, extract site vehicle length and permitted equipment across all providers, filter shared-target results consistently, and revalidate pending alerts.

**Independent Test**: Save two scans on the same campground and dates (one requiring 28 ft, one unrestricted), simulate mixed-length and tent-only openings, and verify shared polling, isolated matching results/counts, and accurate alert delivery/revalidation.

- [x] T017 [P] [US2] Add failing unit tests for `matches_scan_filters` and `matching_scan_results` covering `min_rv_length` (`>=`, `<`, `None` fail-closed, tent-only exclusion) in `tests/db/test_availability.py`.
- [x] T018 [P] [US2] Add failing API validation (`<= 0`, `> 200` -> `422`), `PATCH` omission vs `null` clear, shared-target isolation, and stale outbox invalidation tests in `tests/server/routers/test_scans.py`, `tests/server/routers/test_scan_editing.py`, and `tests/server/routers/test_scan_results.py`.
- [x] T019 [P] [US2] Add failing worker persistence and summary/area alert revalidation tests for `max_vehicle_length` and `permitted_equipment` (including pre-migration outbox rows) in `tests/worker/test_summary_alerts.py` and `tests/worker/test_area_alerts.py`.
- [x] T020 [P] [US2] Add failing site-level `max_vehicle_length` and `permitted_equipment` extraction regressions across `tests/providers/test_recreation_gov.py`, `tests/providers/test_usedirect.py`, `tests/providers/test_going_to_camp.py`, and `tests/providers/test_reserve_america.py`.
- [x] T021 [US2] Extract normalized `max_vehicle_length` (floored positive integer feet; `0`/`None` -> `None`; RV/trailer-compatible equipment only for RV length) and `permitted_equipment` onto `CampsiteDTO` in `src/camply/providers/recreation_gov/provider.py`, `src/camply/providers/usedirect/models/api.py`, `src/camply/providers/going_to_camp/models/api.py`, and `src/camply/providers/reserve_america/models/api.py`.
- [x] T022 [US2] Update `matches_scan_filters` and `matching_scan_results` in `src/camply/db/availability.py` to enforce `min_rv_length` fail-closed while keeping `UniqueTarget.hash` and `UserScan.definition_hash` independent of preferences.
- [x] T023 [US2] Persist `permitted_equipment` and `max_vehicle_length` on `ScanResult` in `src/camply/worker/engine/scanner.py` and include both fields in alert snapshots and `matching_opening` revalidation in `src/camply/worker/engine/alerts.py` and `src/camply/worker/engine/area_alerts.py` (with `.get(...)` safe handling for pre-migration outbox payloads).
- [x] T024 [US2] Add `min_rv_length: int | None` (`ge=1, le=200`) to `ScanCreateRequest`, `ScanUpdateRequest`, and `ScanResponse`, plus `permitted_equipment` and `max_vehicle_length` to `ScanResultItem` in `src/camply/server/schemas.py`, and wire create/PATCH (`model_fields_set` omission vs explicit `None`) and stale intent invalidation in `src/camply/server/routers/scans.py`.

**Checkpoint**: Backend scan CRUD, shared-target polling, and alert delivery enforce equipment length cleanly across all providers.

---

## Phase 5: US3 — Filter saved scans by accessibility and inspect site capabilities (P2)

**Goal**: Support `require_accessible` on saved scans end-to-end and surface persisted equipment, length, hookup, and accessibility capabilities in the React UI.

**Independent Test**: Enable `require_accessible` alongside `min_rv_length` on a scan, verify unknown/false accessibility sites are excluded across results and alerts, and inspect capability badges on `ScanCard`, `ScanDetail`, and `FoundCampsites`.

- [x] T025 [P] [US3] Add failing `require_accessible` tests (explicit `True` passes, `False` and `None` fail closed) across `tests/db/test_availability.py`, `tests/server/routers/test_scans.py`, `tests/server/routers/test_area_scans.py`, `tests/worker/test_summary_alerts.py`, and `tests/worker/test_area_alerts.py`.
- [x] T026 [US3] Implement `require_accessible` filtering in `src/camply/db/availability.py`, `src/camply/worker/engine/alerts.py`, `src/camply/worker/engine/area_alerts.py`, `src/camply/server/schemas.py`, and `src/camply/server/routers/scans.py`, then regenerate and verify OpenAPI types via `task api:generate` and `task api:check`.
- [x] T027 [P] [US3] Add failing UI tests for optional RV length (`1..200` ft, blank/clear, validation errors) and ADA accessibility controls, preference badges, and site capability rows in `src/frontend/components/ScanForm.test.tsx`, `src/frontend/components/ScanCard.test.tsx`, `src/frontend/components/FoundCampsites.test.tsx`, and `src/frontend/pages/ScanDetail.test.tsx`.
- [x] T028 [US3] Update `src/frontend/lib/structs.ts`, `src/frontend/lib/api.ts`, `src/frontend/components/ScanForm.tsx`, `src/frontend/components/ScanCard.tsx`, `src/frontend/components/FoundCampsites.tsx`, and `src/frontend/pages/ScanDetail.tsx` to configure/display RV length and ADA scan filters and show persisted site capabilities (`Up to {N} ft`, permitted equipment, electric, ADA) on matched rows.

**Checkpoint**: Full-stack equipment length, ADA filtering, and site capability display work end-to-end across campground and area scans.

---

## Phase 6: US4 — Provider resilience & backward compatibility (P2)

**Goal**: Verify graceful degradation when providers omit optional metadata and ensure existing pre-upgrade scans and standalone/distributed runtimes remain unaffected.

**Independent Test**: Run upgraded standalone and distributed smoke tests against synthetic partial/missing-metadata providers and pre-upgrade database fixtures.

- [x] T029 [P] [US4] Add synthetic partial/missing-metadata provider resilience regressions in `tests/providers/test_enrichment_refresh.py` and `tests/worker/test_ingestion.py` proving missing optional detail endpoints preserve last verified discovery capabilities without blocking catalog or availability scans.
- [x] T030 [P] [US4] Extend `tests/server/integration/test_standalone_smoke.py` and `tests/server/integration/standalone_fixture.py` to cover pre-upgrade scan preservation, RV length / ADA scan creation and editing, and Explore amenity/RV/ADA filtering.

---

## Phase 7: Polish & Cross-Cutting Verification

- [x] T031 [P] Refresh and inspect affected desktop/mobile light/dark visual baselines (`ScanForm`, `ScanCard`, `ScanDetail`, `SearchPage`) via `task snapshot:update` and `task snapshot:check`.
- [x] T032 [P] Update `docs/architecture/DESIGN_DATA.md`, `docs/architecture/DESIGN_API.md`, `docs/architecture/DESIGN_PROVIDERS.md`, `docs/architecture/DESIGN_FRONTEND.md`, `docs/PLAN.md` (`Phase 3` Advanced Filters), and `docs/CHECKLIST.md` (`T3.2.1b`, `T3.2.2`).
- [x] T033 Run full quality gates (`task fix`, `task lint`, `task check`, `task api:check`, `task test`, `task docs:check`, `task pre-commit -- --all-files`) and record validation outcomes in `docs/specs/20261116-052724-equipment-metadata-filtering/quickstart.md`.
- [x] T034 Run `/speckit-converge` against `docs/specs/20261116-052724-equipment-metadata-filtering/tasks.md` after implementation until `Converged`.

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundation: T003–T008)** blocks all user stories (`US1`–`US4`).
- Within **Phase 2**: `T003` and `T004` run in parallel before `T005`–`T007`; `T008` follows `T006` and `T007`.
- **US1 (Phase 3)** and **US2 (Phase 4)** can proceed independently after Phase 2:
  - Within **US1**: `T009`, `T010`, `T011` run in parallel → `T012`, `T013`, `T014` → `T015` → `T016`.
  - Within **US2**: `T017`, `T018`, `T019`, `T020` run in parallel → `T021` (providers), `T022` (availability), `T023` (worker/alerts), `T024` (API schemas/router).
- **US3 (Phase 5)** builds on `T022`–`T024` (`T025` → `T026` → `T027` → `T028`).
- **US4 (Phase 6)** runs after `US1`–`US3` core paths stabilize (`T029`, `T030` in parallel).
- **Phase 7 (Polish)** follows all story phases (`T031`, `T032` → `T033` → `T034`).

### Parallel Execution Examples

- **Foundation**: Run `T003` (provider length/DTO tests) alongside `T004` (migration/constraint tests).
- **US1**: Run `T009`, `T010`, and `T011` together, then implement `T013` (Recreation.gov RIDB) in parallel with `T014` (UseDirect / GoingToCamp / ReserveAmerica).
- **US2**: Run `T017`–`T020` test authoring in parallel across `db/`, `server/`, `worker/`, and `providers/`.

---

## Requirement Coverage Map

| Requirement / Criterion | Tasks                                          |
| ----------------------- | ---------------------------------------------- |
| `FR-001`                | `T006`, `T011`, `T013`, `T014`                 |
| `FR-002`                | `T009`, `T012`                                 |
| `FR-003`                | `T010`, `T015`, `T016`                         |
| `FR-004`                | `T003`, `T004`, `T011`–`T014`                  |
| `FR-005`                | `T003`, `T005`, `T007`, `T020`, `T021`, `T023` |
| `FR-006`                | `T007`, `T018`, `T024`, `T025`, `T026`         |
| `FR-007`                | `T004`, `T007`, `T018`, `T024`, `T027`, `T028` |
| `FR-008`                | `T017`, `T022`, `T025`, `T026`                 |
| `FR-009`                | `T003`, `T005`, `T017`, `T021`, `T022`         |
| `FR-010`                | `T025`, `T026`                                 |
| `FR-011`                | `T018`, `T024`, `T025`, `T026`                 |
| `FR-012`                | `T018`, `T019`, `T022`, `T023`                 |
| `FR-013`                | `T019`, `T023`, `T025`, `T026`                 |
| `FR-014`                | `T024`, `T027`, `T028`, `T031`                 |
| `FR-015`                | `T004`, `T008`, `T023`, `T030`                 |
| `SC-001`                | `T009`–`T016`, `T033`                          |
| `SC-002`                | `T017`–`T026`, `T033`                          |
| `SC-003`                | `T018`, `T019`, `T022`, `T023`, `T033`         |
| `SC-004`                | `T027`, `T028`, `T031`, `T033`                 |
| `SC-005`                | `T004`, `T008`, `T030`, `T033`                 |

## Implementation Strategy

- **MVP First**: Complete **Phase 1 + Phase 2 + Phase 3 (US1)** or **Phase 4 (US2)** as independent increments; **US1** immediately lights up existing Explore amenity/RV controls (`T3.2.1b`), while **US2** delivers strict equipment length filtering for saved scans and alerts (`T3.2.2`).
- **Incremental Delivery**: Ship **US3** (ADA scan filter + UI site capability badges) and **US4** (partial-provider resilience + standalone smoke) before running final snapshot, documentation, and `/speckit-converge` gates in **Phase 7**.
