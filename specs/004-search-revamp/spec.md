# Search Revamp & Campground Discovery Specification

## User Stories

- **Campground Seekers**: As an outdoor enthusiast, I want to search for campgrounds by name, region, or nearby destination with typo tolerance and compound queries (e.g. "Yosemite Upper Pines") so that I can quickly find the exact facility I want to camp at.
- **Location-Based Explorers**: As a camper planning a road trip, I want to discover campgrounds by state (e.g. California) or geographic radius, and browse them on an interactive map so that I can explore camping options in unfamiliar areas.
- **Specific Rig & Amenity Campers**: As an RV camper, tent camper, or pet owner, I want to filter campgrounds by vehicle length, electrical hookups, pet-friendliness, and site types (Tent, RV, Cabin) so that I only see facilities that accommodate my setup.
- **Monitoring Users**: As a user who finds a sold-out or desirable campground, I want to immediately configure availability monitoring (scans) directly from the search card or map pin with a modern date range picker and weekend quick-presets.

## Requirements

### Backend & Search Engine
1. **Enriched Search Data Model**:
   - The `search` table must store `latitude`, `longitude`, `city`, `state`, `country`, `reservable`, `campsite_types` (JSON list), and amenity flags (`has_electric`, `has_water`, `has_sewer`, `pets_allowed`, `ada_accessible`, `max_rv_length`).
   - Populate these fields during provider metadata sync for recreation areas and campgrounds.
2. **PostgreSQL Full-Text Search & Fuzzy Matching**:
   - Add PostgreSQL `pg_trgm` extension support.
   - Support compound queries and typo tolerance via trigram similarity and weighted `tsvector` full-text search.
3. **Faceted & Geospatial API (`/api/search`)**:
   - Support query parameters: `query`/`q`, `provider_id`, `state`, `campsite_types`, `has_electric`, `min_rv_length`, `pets_allowed`, `lat`, `lng`, `radius_miles`, `page`, `page_size`, `sort_by`.
   - Return paginated results (`items`, `total`, `page`, `page_size`, `total_pages`) along with faceted counts (`facets` by provider, state, campsite types).
   - Maintain backward compatibility for existing callers of `/api/search?query=...`.

### Frontend UI/UX
1. **Dedicated Search & Explore Page (`/search`)**:
   - Implement `/search` route supporting URL query parameter syncing (`?q=...&state=CA&types=RV`).
   - Split layout: Responsive filters sidebar + Result cards + Interactive Map Explorer.
2. **Interactive Map Explorer**:
   - Open-source, zero-API-key mapping with Leaflet or MapLibre displaying campground markers and popups with a "Monitor" CTA.
3. **Global Autocomplete Search Bar**:
   - Update `SearchBar` so typing displays rich autocomplete suggestions, while pressing Enter navigates to `/search?q=...`.
4. **Streamlined Scan Creation (`ScanForm`)**:
   - Support pre-filling campground directly from search cards and map popups.
   - Enhance date selection with intuitive weekend presets and range validation.
