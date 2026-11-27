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

## Concurrency, cooldown, and opt-in proxy rotation

Every provider routes upstream HTTP calls through `BaseProvider.async_client` backed by `RetryTransport` (`src/camply/providers/base.py`), sharing process-wide state keyed by concrete provider class name alongside `ProviderCircuitBreaker`:

- **Shared per-provider cooldown gate (`src/camply/providers/cooldown.py`)**: Enforces bounded in-flight concurrency (`CAMPLY_PROVIDER_MAX_CONCURRENCY`, default `4`), optional cross-instance minimum start spacing (`CAMPLY_PROVIDER_MIN_INTERVAL_SECONDS`, default `0.0`), and monotonic shared HTTP 429 cooldown deadlines (`Retry-After` delta-seconds and RFC 9110 HTTP-date, clamped to `CAMPLY_PROVIDER_MAX_COOLDOWN_SECONDS`). Synchronization primitives are stored per event loop via `WeakKeyDictionary` so sequential `asyncio.run()` tasks never leak or deadlock across closed loops, and concurrency slots are always released before cooldown or retry sleeps.
- **Provider-specific pacing**: Existing per-instance intervals on UseDirect (`1.0s`), GoingToCamp (`0.5s`), and ReserveAmerica (`1.0s`) continue to operate alongside the shared transport gate.
- **Opt-in BYO proxy pool (`src/camply/providers/proxy.py`, `src/camply/providers/transport_config.py`)**: Disabled by default with zero overhead when `CAMPLY_PROXY_URLS` is unset or empty. When configured, requests rotate round-robin across dedicated `httpx2.AsyncHTTPTransport(proxy=..., trust_env=False)` pools with provider-scoped quarantine on HTTP 429/403, global quarantine on proxy/network errors, no quarantine on upstream 5xx, strict fail-closed exhaustion (`wait` vs `fail`, never falling back to direct egress), and strict credential redaction.
- **Observability boundary**: `camply.providers` emits structured logs and dependency-free `TransportEvent` callbacks without importing optional packages; `camply.worker.metrics` registers an observer to publish low-cardinality Prometheus counters and histograms (`camply_provider_cooldown_waits_total`, `camply_provider_cooldown_wait_seconds`, and `camply_provider_proxy_events_total`). Cross-worker distributed cooldown synchronization across separate worker containers remains intentionally out of scope.
