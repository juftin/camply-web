# Data Model: Map Discovery

## Persistent Data

Reuse `Search` as the source of discovery metadata. No table, column, index, or migration is planned initially. Coordinates remain provider-supplied nullable floats. Existing provider/entity/name/amenity fields determine search membership and actions. Measure query plans before considering an index change.

## Search Context

Reuse current `query`/`q`, provider, entity type, state, electric, pets, RV length, and optional radius inputs. Canonical map query keys contain only matching predicates; omit list page, page size, and sort. This context is shared by all three endpoints and member-page requests.

Explicit false amenity values filter for rows without that amenity, matching current Explore search. Existing nonpositive RV and partial-radius semantics remain unchanged. Empty text with no filters means all catalog matches for Explore and map endpoints. The flat autocomplete endpoint retains its existing empty-query behavior.

## Geographic Bounds

| Field       | Meaning                                                                       |
| ----------- | ----------------------------------------------------------------------------- |
| west/east   | Finite longitudes in [-180, 180]; west > east means crossing the antimeridian |
| south/north | Finite latitudes in [-90, 90]                                                 |

Summary bounds can be degenerate for a single/co-located point; no mappable locations yield null bounds. Request viewports must have positive height and width; full world is explicitly west=-180/east=180. Frontend expansion of degenerate summary bounds is a display concern.

Canonical indexing/comparison uses longitude 180 as -180. Place metadata preserves original coordinates. Accept zero; reject null, nonfinite, or out-of-range coordinates for mapping without removing those rows from list results.

## Summary

Fields: `total`, `mappable_total`, `unmappable_total`, `bounds`.

Invariants: total = mappable_total + unmappable_total; bounds is null iff mappable_total is zero. Counts cover the complete filtered set, not the current list page or map viewport. Use the complement of the largest sorted longitude gap for circular bounds, deterministically breaking tied gaps by their starting longitude.

## Geographic Grid and Map Features

Grid levels range 1–20. At level L, cell width/height in degrees is 360 / 2^L; there are 2^L columns and 2^(L-1) rows. Longitude and latitude are shifted into nonnegative domains before integer division/casting. Longitude 180 joins -180; latitude 90 belongs to the final row. Cell IDs are `L:x:y` with validated integer ranges.

Choose the finest level no greater than min(requested zoom + 2, 20) whose cells intersecting the request viewport total at most 512. Count a wrapped viewport's column union, not duplicated columns. Use the same inclusive viewport edges when computing that upper bound as when filtering rows. This is a bound established before SQL aggregation, not a LIMIT that silently drops cells.

- **Location feature**: `kind=location`, `cell_id`, and `item` containing the existing SearchResultResponse. Its cell has exactly one matching mappable location inside the viewport.
- **Group feature**: `kind=group`, `cell_id`, `count` >=2, representative latitude/longitude, and member bounds. Centers and bounds describe only matching members in the captured viewport. Because cells do not cross the canonical longitude seam, arithmetic centers remain within the cell. Member bounds can be degenerate.

Viewport response fields: `viewport`, `grid_level`, `represented_total`, `features`. Feature counts sum to represented_total; features length <=512. Outside-viewport matches remain discoverable by panning. Do not conflate represented_total with global mappable_total.

## Group-Member Page

Inputs: canonical search context, selected `cell_id`, captured viewport, optional `after_id`, and bounded `page_size`. Outputs: `items`, `total`, `next_cursor`.

Member rows satisfy all filters, coordinate validity, viewport inclusion, and exact cell membership. Order by Search.id ascending and use Search.id > after_id for subsequent pages. Fetch page_size + 1 to determine whether another page exists; return at most page_size items. No cursor means the end. Existing qualified Search IDs prevent collisions; explicit provider/entity/external IDs still drive Details and Monitor.

The member total matches the selected group's count on an unchanged catalog. Metadata refreshes between requests may alter totals; no cross-request snapshot is promised.

## Frontend State and Transitions

| State/event            | Behavior                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| Open Explore           | Show map above list; request global summary and then the fitted viewport                         |
| Collapse/reopen map    | Hide/show only the map; retain filters, list page and camera for unchanged filters               |
| Filter change          | Reset page as today, clear selection/member cursor, update list and summary, fit new bounds once |
| Page or sort change    | Update list only; keep map membership, extent, and selection                                     |
| Move/zoom end          | Debounce viewport query; preserve global filters, list totals and page                           |
| Select group           | Capture its cell ID and response viewport; offer zoom and View places                            |
| Select member/location | Show React summary and exact Details/Monitor actions                                             |
| Close scan form        | Preserve filters, list page and extent                                                           |
| Resize map             | Restore parent-held extent and resize the MapLibre canvas                                        |
| Browser navigation     | Restore URL filters/page and synchronize search input; refit only for a changed filter context   |
| Summary/viewport error | Mark failed state, preserve usable list, retry the failed query                                  |
| Tile error             | Nonblocking basemap status; preserve markers/list and retry ordinary tile loading                |

Selections are ephemeral. Global summaries, viewport results, and member pages use separate query keys and current-key guards; stale responses cannot replace a newer context. Basemap settings are public deployment configuration, not user profile data.
