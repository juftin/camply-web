# Tasks: Search Revamp & Campground Discovery

## Phase 1: Database & Data Layer
- [x] T1.1: Create Alembic migration to add enriched columns, pg_trgm extension, and indexes to the `search` table.
- [x] T1.2: Update `Search` ORM model in `db/models/search.py` with enriched columns and composable search query builder.
- [x] T1.3: Update `BaseProvider` search statements in `providers/base.py` to populate new columns.
- [x] T1.4: Update and verify DB model and provider tests.

## Phase 2: Backend Search API & Engine
- [x] T2.1: Implement advanced search algorithm with fuzzy/trigram matching, multi-criteria filters, and geo-distance calculations.
- [x] T2.2: Update `search_router` in `backend/routers/search.py` and schemas in `backend/schemas.py`.
- [x] T2.3: Generate API types (`task api:generate`) and verify contract checks (`task api:check`).
- [x] T2.4: Write backend search tests covering queries, filters, facets, and pagination.

## Phase 3: Frontend Search & Explore UI
- [x] T3.1: Create dedicated `/search` route and `SearchPage` with filter sidebar, results grid, and sorting.
- [x] T3.2: Integrate campground discovery layout with interactive cards, badges, and filters.
- [x] T3.3: Update `SearchBar` to navigate to `/search?q=...` on Enter while retaining fast autocomplete.
- [x] T3.4: Write frontend tests for search page, filter interactions, and URL parameter syncing.

## Phase 4: Scan Creation & End-to-End Integration
- [x] T4.1: Connect search result cards directly to `ScanForm` with pre-filled facility data.
- [x] T4.2: Add weekend quick-presets and improved date range validation to `ScanForm`.
- [x] T4.3: Verify all tests (`task test`), type checking (`task check`), and linting (`task lint`).
