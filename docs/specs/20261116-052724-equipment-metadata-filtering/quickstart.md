# Quickstart Validation Guide: Equipment Metadata and Filtering

**Feature**: `20261116-052724-equipment-metadata-filtering`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Prerequisites

- Python >=3.11 (default 3.14) and Node / pnpm installed (`task doctor`).
- Dependencies synced (`task install`).
- **Implementation baseline (`d3974ac`, 2026-11-16)**: `uv 0.13.1`, `Python 3.14.7`, `Node v22.23.4`, `pnpm 12.15.0`, `Task 3.54.0`; pre-edit `task lint`, `task check`, `task api:check`, `task docs:check`, and `task test` clean on `origin/main`.

## Validation Scenarios

### 1. Migration Upgrade, Downgrade & Existing Scan Preservation

- Verify the additive Alembic migration upgrades cleanly from the prior head (`2d7ab29d3a46`), preserves existing `campgrounds`, `scan_results`, and `user_scans` with `require_accessible = false` and `min_rv_length = null`, enforces check constraints on invalid lengths (`0`, `-5`, `201`), and downgrades without error:
  ```bash
  task backend:test -- tests/db/test_equipment_migration.py
  ```

### 2. Provider Metadata & Site Capability Extraction

- Verify Recreation.gov (RIDB + campsite search), UseDirect, GoingToCamp, and ReserveAmerica populate `Campground` discovery capabilities, aggregate parent `RecreationArea` capabilities in `search`, and extract `max_vehicle_length` / `permitted_equipment` / `is_accessible` onto `CampsiteDTO` with conservative floor/unknown handling:
  ```bash
  task backend:test -- tests/providers/test_recreation_gov.py tests/providers/test_usedirect.py tests/providers/test_going_to_camp.py tests/providers/test_reserve_america.py
  ```

### 3. Shared-Target Polling, Matching & Outbox Revalidation

- Verify `matches_scan_filters`, `matching_scan_results`, API scan CRUD (`PATCH` omission vs `null` clear), and worker alert revalidation (`alerts.py`, `area_alerts.py`) isolate multiple users sharing one campground target with distinct RV length and ADA requirements:
  ```bash
  task backend:test -- tests/db/test_availability.py tests/server/routers/test_scans.py tests/server/routers/test_scan_results.py tests/server/routers/test_search.py tests/worker/test_summary_alerts.py tests/worker/test_area_alerts.py
  ```

### 4. Frontend UI, OpenAPI Contract & Visual Baselines

- Verify generated TypeScript schema matches FastAPI OpenAPI (`task api:check`), Explore ADA/RV/amenity filters work on list and map views, `ScanForm` validates/saves/clears `min_rv_length` and `require_accessible`, and `FoundCampsites` displays site capabilities cleanly on desktop and mobile:
  ```bash
  task api:check
  task frontend:test
  task snapshot:check
  ```

### 5. Full Quality Gates

```bash
task fix
task lint
task check
task test
task docs:check
```

## Validation Outcomes (2026-11-16)

- **`task fix` & `task lint`**: Passed (`ruff format --check` 309 files, `ruff check`, `lint-imports` 6 kept / 0 broken, `oxlint` 0 warnings / 0 errors across 145 files, `oxfmt --check` 403 files).
- **`task check`**: Passed (`mypy` 179 source files + native `tsc` for `src/frontend` and `src/frontend/functions`).
- **`task api:check`**: Passed (`build/openapi.json` matches `src/frontend/lib/api/generated/schema.ts`).
- **`task docs:check`**: Passed (VitePress build clean).
- **`task test`**: Passed:
  - `backend:test`: `2161 passed, 23 skipped` (opt-in PostgreSQL migration tests and `CAMPLY_STANDALONE_SMOKE` skipped unless enabled).
  - `backend:packaging:test`: `81 passed`.
  - `frontend:test`: `46` test files, `474` tests passed.
  - `frontend:build:standalone` & `frontend:pages:check`: `2` test files (`10` tests) and Pages verification passed.
- **`task pre-commit -- --all-files`**: All Python/YAML/AST/TOML/ruff/import-linter hooks passed; `oxfmt --all-files` failed on pre-existing Go/Helm templates (`deploy/helm/templates/*.yaml`), while changed feature files pass `oxfmt` and pre-commit hooks cleanly.
- **`task snapshot:check`**: Local Linux Chromium captures differ from macOS CI baselines on existing text-bearing views due to font rendering; `scan-form-dialog-desktop-light-diff.png` visually inspected to verify new controls render cleanly.
