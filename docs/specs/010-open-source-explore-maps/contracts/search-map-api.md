# Contract: Search Map API

**Status**: Planned additive interface; endpoints do not exist yet.

All routes are public read-only catalog discovery under `/api`. They do not call booking providers, create scans, require invitation eligibility, or expose private user data. Existing search routes/responses remain compatible. FastAPI response models in `backend/schemas.py` are the implementation's source of truth; generate frontend aliases from OpenAPI rather than duplicating these DTOs manually.

## Shared Search Inputs

Use the same names and semantics as `/api/search/explore`:

| Input                      | Semantics                                                                                      |
| -------------------------- | ---------------------------------------------------------------------------------------------- |
| query, q                   | Optional text; q overrides query even when empty; trim/normalize through existing search logic |
| provider_id, entity_type   | Existing single-provider/entity filters                                                        |
| state                      | Existing case-insensitive state filter                                                         |
| has_electric, pets_allowed | True/false constrains the selected amenity; absent leaves it unconstrained                     |
| min_rv_length              | Existing positive minimum; nonpositive/absent adds no constraint                               |
| lat, lng, radius_miles     | Existing approximate radius box when all are present and radius is positive                    |

Map clients omit page, page_size, and sort_by except the member endpoint's own page_size. Those list presentation values must never change map membership. Extra list parameters, if present, are ignored. Map endpoint validation must not reinterpret existing filter defaults.

All routes use the same combined attribute/text predicate assembly as the list. Select SQLite/PostgreSQL matching from the actual session dialect. No-query/no-filter requests cover the full Explore catalog.

## GET /api/search/map/summary

Inputs: shared filters only.

Response `SearchMapSummaryResponse`:

| Field            | Type and meaning                                          |
| ---------------- | --------------------------------------------------------- |
| total            | Nonnegative count of all matching rows                    |
| mappable_total   | Matching rows with finite coordinates in geographic range |
| unmappable_total | total minus mappable_total                                |
| bounds           | Nullable GeographicBounds for all mappable matches        |

`GeographicBounds` contains numeric `west`, `south`, `east`, `north`. Longitude is canonicalized to [-180, 180); a west greater than east denotes dateline crossing. Summary bounds may have equal endpoints. The full-world request convention is described below. With zero mappable results, bounds is null; with one/co-located positions, it is a point. Circular longitude bounds use the complement of the largest gap, with deterministic tie handling.

Example with dateline neighbors and one unmappable match:

```json
{
  "total": 3,
  "mappable_total": 2,
  "unmappable_total": 1,
  "bounds": { "west": 179.5, "south": -17.8, "east": -179.5, "north": -17.6 }
}
```

## GET /api/search/map

Inputs: shared filters plus all five required viewport inputs:

| Input        | Validation                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| west, east   | Finite [-180, 180]; west > east means crossing; west=-180/east=180 means full world; equal endpoints rejected |
| south, north | Finite [-90, 90]; south < north                                                                               |
| zoom         | Integer 0–19                                                                                                  |

Use inclusive viewport edges. A normal longitude interval applies AND; a crossing interval applies OR. Normalize catalog longitude 180 to -180 before comparison. Special-case the full-world interval to cover every valid longitude exactly once. Frontend normalizes bounds after panning across repeated worlds and extends polar edge latitudes to ±90 when necessary.

Response `SearchMapResponse`:

| Field             | Type and meaning                                            |
| ----------------- | ----------------------------------------------------------- |
| viewport          | GeographicBounds actually used, echoed for member selection |
| grid_level        | Integer 1–20 chosen by the server                           |
| represented_total | Count of matching mappable rows inside this viewport        |
| features          | Discriminated location/group union, maximum 512 entries     |

`SearchMapLocation` fields:

- `kind`: literal `location`.
- `cell_id`: validated grid identifier.
- `item`: the existing `SearchResultResponse`, including original coordinates, provider, entity type, campground/recreation IDs, names, and metadata required for Details/Monitor.

`SearchMapGroup` fields:

- `kind`: literal `group`.
- `cell_id`: grid identifier `level:x:y`.
- `count`: integer >=2.
- `latitude`, `longitude`: finite arithmetic center of the matching members in this viewport, calculated using canonical longitude.
- `bounds`: GeographicBounds of those same members, possibly degenerate.

The group includes both entity types and providers; it never pretends to be a campground. Feature ordering is deterministic by grid row then column. A location contributes one to represented_total; a group contributes count. The server must aggregate the entire matching viewport, never LIMIT an overfull list of arbitrary groups. Grid arithmetic, pre-query coarsening, and pole/seam rules are in [data-model.md](../data-model.md).

For a full-world request, represented_total equals mappable_total on an unchanged catalog. For a narrower viewport, the interface labels the represented count as in-view, keeping the global summary separate. Panning changes neither the global filters nor list counts. Out-of-view places are discoverable through map navigation.

## GET /api/search/map/members

Inputs: shared filters, the selected feature's captured `west/south/east/north`, `cell_id`, optional `after_id`, and `page_size`.

- `cell_id` must contain exactly three decimal integers. Level is 1–20; x is in [0, 2^level); y is in [0, 2^(level-1)).
- `page_size` defaults to 50 and ranges from 1 to 100. It is independent of list pagination.
- `after_id` is the previous response's next_cursor, maximum length 128 to match Search.id. Treat it as an opaque string; do not parse provider or booking IDs from it.
- Both the grid predicate and original viewport apply. Group count, bounds, and member population therefore describe the same set.

Response `SearchMapMembersResponse`:

| Field       | Type and meaning                                                               |
| ----------- | ------------------------------------------------------------------------------ |
| items       | At most page_size existing SearchResultResponse objects                        |
| total       | Current number of matching mappable members in this cell and captured viewport |
| next_cursor | Last returned Search.id when another page exists; otherwise null               |

Order by Search.id ascending. Request later pages with id > after_id and fetch at most page_size + 1 internally. The client does not automatically exhaust pages; expose Load more. Every group offers View places regardless of zoom, so identical-coordinate members remain selectable. Filters changing clear group selection and cursor; subsequent requests always carry the original selection's captured context.

## Errors, Consistency, and Limits

- Return 422 for missing/invalid viewport values, nonfinite numbers, invalid cell identifiers, or invalid member page sizes. Use ordinary FastAPI validation responses.
- A valid viewport/cell with no matches returns 200 with empty features/items and zero counts. Summary total can remain positive when none of the matches is mappable.
- Transport/server failures remain failures, never successful empty results. The UI distinguishes summary, viewport, and member failure states and retries only the failed query.
- Counts and membership reflect each request's current catalog. A concurrent metadata refresh can change totals between requests. Do not invent snapshot tokens or shared server state; the UI offers refresh when it detects conflicting global counts or a changed selected-group total.
- Response sizes are bounded by aggregation and keyset pages; database filtering/grouping is not constant-time. Do not download all coordinates into Python or all list pages into the browser. Measure both SQLite and PostgreSQL behavior before release.
- Expose no account data, credentials, private scan settings, or provider API responses in these routes. Existing protected scan endpoints retain their access checks when Monitor is used.

## Required Contract Verification

Parity cases include blank queries, compound/fuzzy text, provider/entity/state filters, true/false amenities, RV lengths, optional radius, and combinations. Compare map/global membership to the complete filtered set in the database, not only list page one. Traverse every member cursor on a fixture containing >100 co-located places and reused external IDs. Cover inclusive cell/viewport boundaries, ±180, poles, zero, invalid coordinates, wrapped/full-world viewports, and feature caps at every zoom. Run representative cases on live PostgreSQL as well as SQLite and gate generated types with `task api:check`.
