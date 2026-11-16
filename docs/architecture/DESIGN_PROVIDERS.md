# Provider Architecture

`camply.providers` defines a shared async adapter layer so the web worker, standalone runtime, and foreground CLI talk to every reservation system through one contract.

## Core interface and DTO

Every provider subclasses `BaseProvider` and translates upstream API responses into Pydantic models before returning unified `CampsiteDTO` objects:

- **`find_availabilities(park_id, start_date, end_date)`:** Queries availability for one campground (`end_date` is exclusive checkout) and returns `CampsiteDTO` records with `campsite_id`, `campsite_name`, `campsite_type`, `capacity`, `available_dates`, `is_electric`, `is_accessible`, `permitted_equipment`, `max_vehicle_length` (floored whole feet, or `None`), and `metadata`.
- **`populate_database()` / `sync_metadata()`:** Refreshes `recreation_areas`, `campgrounds`, and `search` atomically, incrementing `providers.catalog_revision` so stale references disable cleanly without breaking existing scans.
- **`enrich_metadata()`:** Optionally caches `DestinationDetails` photos and practical visitor info (up to 100 stale destinations per pass, 7-day freshness, 1-hour retry cooldown) for Recreation.gov, UseDirect providers, and ReserveAmerica.

## Direct upstream search and target resolution

The foreground CLI queries providers without a local database using `BaseProvider`:

- **`search(query, state, recreation_area_id, entity_type, limit)`:** Queries upstream discovery endpoints directly via `search_upstream()`, supporting `SearchEntityType.CAMPGROUND`, `SearchEntityType.RECREATION_AREA`, or combined results (`limit` 1–1000).
- **`get_campground(id)` / `get_recreation_area(id)`:** Resolves an exact opaque native ID regardless of discovery page limits.
- **`iter_campgrounds(recreation_area_id)`:** Expands every eligible overnight campground in a recreation area after validating complete metadata pages.

## Supported provider families

| Family                  | Providers                                                                                             | Notes                                                                                                                                                                           |
| ----------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Recreation.gov**      | `RecreationDotGov`                                                                                    | Uses RIDB catalog archives (parsed in memory before commit) and `/api/search` upstream relevance.                                                                               |
| **UseDirect / Tyler**   | `ReserveCalifornia` and 9 state/regional parks (FL, VA, MN, OH, AZ, MO, Fairfax, Oregon Metro, NT AU) | Shared `UseDirectProvider` async RDR client with 1 req/sec per-instance pacing and explicit non-electric group overrides.                                                       |
| **GoingToCamp (Camis)** | `WashingtonStateParks` and 13 US/Canadian regional systems                                            | Shared `GoingToCampProvider` resolving overnight booking categories and BFS child loop maps in 60-night windows.                                                                |
| **ReserveAmerica**      | `ReserveAmerica`                                                                                      | Uses `a1.reserveamerica.com/jaxrs-json` with anonymous cookie session refresh, 14-day product grids, and composite `{contract}_{facility}` IDs without parent recreation areas. |

## Concurrency and pacing

All providers share a single `httpx.AsyncClient` retry/circuit-breaker transport per instance and enforce per-instance pacing (such as 1 request/second on UseDirect and ReserveAmerica). Cross-worker distributed rate limiting is not currently shared across separate worker containers.
