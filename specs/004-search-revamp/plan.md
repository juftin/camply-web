# Implementation Plan - Search Revamp & Discovery

## Technical Architecture

### 1. Data Layer (`backend/packages/db`)
- Create an Alembic migration:
  - Add `pg_trgm` extension if not exists.
  - Add columns to `search` table: `city`, `state`, `country`, `latitude`, `longitude`, `reservable`, `campsite_types`, `has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`, `search_vector`.
  - Add GIN indexes on `search_vector`, `campground_name` (trgm), `recreation_area_name` (trgm), and composite index on `(latitude, longitude)`.
- Update `Search` ORM model in `backend/packages/db/db/models/search.py`.
- Update SQL insert statements in `BaseProvider` (`backend/packages/providers/providers/base.py`) to map these columns when populating the search table from `RecreationArea` and `Campground`.

### 2. Provider Ingestion (`backend/packages/providers`)
- Ensure `RecreationGovProvider` populates campground and rec area city, state, country, lat/long, and amenities into `Campground` and `RecreationArea` tables.
- Update `BaseProvider.populate_search_table` to include the enriched attributes.

### 3. API & Search Engine (`backend/packages/backend`)
- Modernize `Search.algorithm` in `db.models.search`:
  - Build composable query filters:
    - Text query: Trigram matching + Full-text search ranking.
    - State filter: `cls.state.ilike(...)` or `in_(states)`.
    - Provider filter: `cls.provider_id.in_(provider_ids)`.
    - Campsite types: JSONB / array contains check.
    - Amenity filters: `has_electric`, `pets_allowed`, `max_rv_length >= min_rv_length`.
    - Geospatial radius: Haversine distance formula calculation.
  - Compute faceted aggregation counts efficiently.
- Update `backend/packages/backend/backend/routers/search.py`:
  - Support both `query` and `q`, pagination params (`page`, `page_size`), and filter params.
  - Return `SearchResultResponse` or rich `SearchResponse` (with backward compatibility).
- Regenerate API client types via `task api:generate`.

### 4. Frontend UI/UX (`frontend/src`)
- Add `/search` route in `frontend/src/App.tsx`.
- Create `SearchPage.tsx` with:
  - Filter sidebar (State selector, Campsite types, Amenities, RV length).
  - Search results grid with rich `CampgroundCard`s.
  - Interactive map (using Leaflet / OpenStreetMap tiles for zero-API-key self-hosting).
- Update `SearchBar.tsx`:
  - Handle keyboard `Enter` to navigate to `/search?q=...`.
  - Keep responsive autocomplete dropdown for quick navigation.
- Upgrade `ScanForm.tsx` to pre-select campground from search result cards and map pins.

### 5. Verification & Testing
- Unit tests for DB models, migrations, and search algorithm (`backend/packages/db/tests`, `backend/packages/backend/tests`).
- Frontend component tests for `/search`, `SearchBar`, and `ScanForm` (`frontend/src/test`).
- Full quality gates: `task test`, `task check`, `task lint`.
