# DESIGN_PROVIDERS: Provider Architecture & Logic Migration

This document outlines the architecture for the provider layer in `camply`, focusing on a standardized interface, provider-specific Pydantic models, and the logic migration from the legacy CLI.

## Python package boundaries

Provider APIs live in `camply.providers` within the single `camply`
distribution. They may use `camply.db` persistence, but must not import server
or worker application bootstrap. Providers and SQLite are base dependencies;
HTTP serving, Celery/Redis, PostgreSQL, and Sentry remain optional extras.

## 🎯 Architecture Goals

1. **Standardization**: All providers must return a unified `CampsiteDTO` to the worker.
2. **Isolation**: Each provider maintains its own internal Pydantic models (matching the source API).
3. **Translation**: Explicit translation layers (`to_campsite`) convert raw API data to the unified DTO.
4. **Maintenance**: Background tasks for periodic metadata updates (Park names, locations, types).

---

## 🏗️ Core Interface: `BaseProvider`

Every provider must inherit from this ABC to ensure compatibility with the **Smart Poller**.

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique slug: e.g., 'recreation_dot_gov'"""
        pass

    @abstractmethod
    async def find_availabilities(
        self,
        park_id: str,
        start_date: date,
        end_date: date
    ) -> List[CampsiteDTO]:
        """
        The primary scan method.
        Calls internal API, parses into internal models,
        and translates to CampsiteDTO.
        """
        pass

    @abstractmethod
    async def sync_metadata(self) -> None:
        """
        Background task to update the 'Search' and 'Campground'
        tables with the latest info from the provider.
        """
        pass
```

---

## 📦 The Unified DTO: `CampsiteDTO`

This is the only object the **Worker** ever sees.

- `campsite_id`: `String` (Unique within provider)
- `campsite_name`: `String`
- `campsite_type`: `CampsiteType` (Enum: TENT, RV, CABIN, etc.)
- `capacity`: `Integer`
- `available_dates`: `List[Date]`
- `is_electric`: `Boolean`
- `is_accessible`: `Boolean`
- `metadata`: `Dict[String, Any]` (Provider-specific raw attributes)

---

## 🔄 Logic Migration Strategy

Instead of wrapping the legacy `cli/` code, we are migrating the core "Scraping" logic to ensure it fits our new **async-first** and **multi-tenant** architecture.

### 1. Internal Pydantic Models

We will copy and refine the Pydantic models from `cli/camply/containers/api_responses.py` into each provider's `models/` subdirectory.
_Example_: `src/camply/providers/recreation_gov/models/api.py`.

### 2. The Translation Layer

Each internal API model will implement a conversion method:

```python
class RecDotGovCampsite(PydanticBaseModel):
    # ... raw API fields ...

    def to_dto(self) -> CampsiteDTO:
        return CampsiteDTO(
            campsite_id=str(self.campsite_id),
            campsite_name=self.name,
            # ... mapping logic ...
        )
```

---

## 🛠️ Background Tasks

To keep the system running smoothly, providers are responsible for more than just scanning:

1. **Metadata Refresh**:
   - _Frequency_: Weekly.
   - _Task_: Download full campground lists (e.g., RIDB export for Recreation.gov) and update the `Search` table so users can find new parks in the UI.
2. **Stale Result Cleanup**:
   - _Frequency_: Daily.
   - _Task_: Purge entries from `scan_results` that are in the past or no longer relevant.
3. **Provider Health Check**:
   - _Frequency_: Hourly.
   - _Task_: Perform a "noop" search to ensure the provider API hasn't changed its structure or blocked our IP.

---

## 🔒 Performance & Concurrency

- **Connection Pooling**: Use a shared `httpx2.AsyncClient` within the provider package.
- **Async-First**: All IO-bound operations must be `async` to prevent blocking the worker.
- **Rate Limiting**: Implementation of provider-specific backoff logic to respect API limits.

## ReserveCalifornia

`ReserveCaliforniaProvider` is registered as provider ID **2**. It uses the current `https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr` API. The former `calirdr.usedirect.com` host and hash-based booking links are retired.

- `fd/places` supplies recreation areas (`PlaceId`); `fd/facilities` supplies campgrounds (`FacilityId`). String IDs are preserved and search joins include both park and provider IDs.
- `search/filters` resolves equipment and unit-type groups. `search/grid` receives facility IDs and inclusive date windows of up to 30 nights. The adapter treats the scan's `end_date` as check-out and clips padded responses to each requested window.
- HTTP 200 responses with `NightsActual=0` indicate rejected grid requests and raise an error, preserving the worker's previous results. A valid grid with no units still returns no availability.
- Only free overnight (`UseType=4`) units that permit online booking are returned. Blocks, walk-in nights, reservation locks, draws, explicitly closed seasons, and hidden/filtered units are excluded. Composite grid keys are not campsite IDs; the DTO uses `UnitId`.
- Unknown capacity is `0`. Electrical hookups require an explicit electrical group; water/sewer hookups do not imply electricity. Equipment names, vehicle length, classification IDs, and per-night minimum stays are retained in metadata. Provider minimum-stay rules are not yet enforced by the shared worker.
- Requests share the base retry/circuit-breaker transport and are paced at one request per second within an instance. This is not a distributed rate limit across workers.
- Metadata and search refreshes commit together. Upstream records that disappear are disabled without deleting scan references; hidden parks and unbookable campgrounds are excluded from search. Seed migration downgrade refuses to remove provider identity while dependent data exists, including on SQLite without foreign-key enforcement.
- Booking routes are `/park/{PlaceId}/{FacilityId}`. API serialization and notifications supply the parent park ID to `get_campground_url`; without that context, the method returns the booking homepage.

Apply the provider seed migration with `task backend:migration-upgrade`. With Celery Beat and a worker running, ingestion refreshes registered providers daily at midnight UTC. Worker startup does not currently trigger ingestion. For a manual refresh, run `task backend:run -- camply db metadata --provider-id 2` (the CLI defaults to Recreation.gov for compatibility).

Metadata ingestion is independent of availability scans and requires no campground selection or date range. `sync_metadata()` delegates to `populate_database()`, fetching the complete parks and facilities catalogs and updating `providers`, `recreation_areas`, `campgrounds`, and `search`. Nameless entries and facilities without a known parent park are omitted. Hidden and offline records are retained in metadata with their visibility/bookability flags; searchable campgrounds must be enabled and reservable. Individual campsite/unit metadata and filter dictionaries are not persisted: the current schema has no `campsites` table, and those details are parsed when scanning availability.

Regression tests use generated synthetic responses, including a VCR replay with request-body matching through the real retry transport. Public metadata and availability endpoints were also verified live on 2026-10-12; live responses and reservation identifiers are not stored in test fixtures. See [the feature plan](../specs/005-reserve-california/plan.md).

## Shared UseDirect / Tyler providers

`UseDirectProvider(BaseProvider, ABC)` in `providers.usedirect.provider` owns the shared async RDR requests, per-instance pacing/cache, date-window aggregation, and atomic metadata/search refreshes. Shared source models live in `providers.usedirect.models`; no backend provider imports the legacy CLI. Concrete variations supply the inherited abstract provider identity plus `api_url`, `booking_url`, and `state_code`. `country_code` defaults to US and is AU for Northern Territory. Provider and park IDs scope all catalog updates and search joins.

All concrete UseDirect providers live in `providers.usedirect.variations`:

| ID  | Provider              | State / country | Booking behavior                              |
| --- | --------------------- | --------------- | --------------------------------------------- |
| 2   | ReserveCalifornia     | CA / US         | `/park/{PlaceId}/{FacilityId}`                |
| 3   | Florida State Parks   | FL / US         | `/Web/#!park/{PlaceId}/{FacilityId}`          |
| 4   | Virginia State Parks  | VA / US         | `/Web/#!park/{PlaceId}/{FacilityId}`          |
| 5   | Minnesota State Parks | MN / US         | `/MinnesotaWeb/#!park/{PlaceId}/{FacilityId}` |
| 6   | Ohio State Parks      | OH / US         | `/OhioCampWeb/#!park/{PlaceId}/{FacilityId}`  |
| 7   | Arizona State Parks   | AZ / US         | `/reserve/#!park/{PlaceId}/{FacilityId}`      |
| 8   | Missouri State Parks  | MO / US         | `/MSPWeb/#!park/{PlaceId}/{FacilityId}`       |
| 9   | Fairfax County Parks  | VA / US         | Opens `/FairfaxFCPAWeb` reservation search    |
| 10  | Oregon Metro          | OR / US         | Opens `/MetroWeb` reservation search          |
| 11  | Northern Territory    | NT / AU         | Opens `/Web` reservation search               |

The new seed migration adds IDs 3–11. Metadata sync remains independent of availability and includes all valid parks/facilities from the complete catalogs, including offline records. Source state codes are normalized; blank fields and full state names use the concrete provider's two-letter fallback. Explicit non-electric groups (seen in Ohio and Fairfax) override electrical substring matches.

Apply migrations with `task backend:migration-upgrade`, then populate any provider with `task backend:run -- camply db metadata --provider-id 3` (Florida in this example). `task backend:run -- camply db metadata --help` lists every registered ID. The existing ingestion orchestrator fans out all registered providers and Celery Beat schedules it daily at midnight UTC. Initial population remains manual; worker startup does not trigger it.

On 2026-10-12, all nine added providers responded to park/facility catalogs, filters, sample overnight grids, and public booking-page checks. API roots and booking hosts are fixed in each concrete variation; Virginia uses a Tyler host, and Ohio/Missouri use their current reservation hosts. Regional providers keep the CLI's search-page fallback until facility deep links are separately verified.

Alabama State Parks and Maricopa County's legacy catalog endpoints returned HTTP 404. They are not registered or seeded. See [UseDirect TODOs](../specs/007-usedirect-providers/TODO.md) for endpoint discovery and other known limits, and [the implementation plan](../specs/007-usedirect-providers/plan.md) for scope and verification. Shared worker minimum stays, residency-aware booking windows, cross-worker rate limiting, and individual campsite persistence remain follow-ups.

## GoingToCamp & Washington State Parks

`GoingToCampProvider(BaseProvider, ABC)` in `providers.going_to_camp.provider` implements the shared async adapter for Camis GoingToCamp reservation systems, with Pydantic v2 metadata and inventory models in `providers.going_to_camp.models`. Because every GoingToCamp website independently assigns `transactionLocationId` and `resourceLocationId` sequences starting at `-2147483648` (`INT32_MIN`), each deployment is modeled as a concrete variation in `providers.going_to_camp.variations` with its own permanent `Provider` ID rather than hardcoding fake recreation-area IDs.

| ID  | Provider               | State / country | Booking behavior                                                                         |
| --- | ---------------------- | --------------- | ---------------------------------------------------------------------------------------- |
| 12  | Washington State Parks | WA / US         | `/create-booking/results?resourceLocationId={FacilityId}&transactionLocationId={ParkId}` |

- `GET /api/transactionlocation` supplies parks (`RecreationArea`), and `GET /api/resourceLocation` supplies campgrounds/facilities (`Campground`) with `rootMapId` directly on each location.
- Active overnight camping and lodging categories are resolved dynamically from `GET /api/bookingcategories` (`bookingModel = 0`, `isDisabled != true`, excluding marina/moorage categories) and `GET /api/resourcecategory` (`resourceType in (0, 3)`, excluding harbor slips/buoys while preserving marine-trail and boat-in camping). Day-use, marina, and unmapped facilities remain in `campgrounds` with `reservable = false` and are excluded from searchable `Campground` rows in `search`.
- Availability scans fetch bulk facility site metadata once via `GET /api/resourcelocation/resources?resourceLocationId={id}` and query daily statuses in bounded 60-night windows via `GET /api/availability/map?getDailyAvailability=true&isReserving=true`. Child loop maps in `mapLinkAvailabilities` are traversed via BFS only when statuses indicate open inventory (`0 = Available` or `7 = PartiallyAvailable`), and only daily status `0` (`Available`) is treated as bookable online (`end_date` is exclusive check-out). Unknown campground IDs raise `ValueError` so cached worker scan results are preserved.
- Equipment lookups span all `equipmentCategories` from `GET /api/equipment`, and site attributes from `GET /api/attribute/filterable` decode both scalar and multi-select enum values (e.g., `["20 Amps", "30 Amps", "50 Amps"]`). `is_electric` checks electrical attributes while excluding explicit non-electric values, and `is_accessible` checks dedicated accessibility attributes rather than adjacent amenities.
- Populate Washington State Parks manually with `task backend:run -- camply db metadata --provider-id 12` after `task backend:migration-upgrade`. Remaining GoingToCamp deployments from the legacy CLI are tracked in [GoingToCamp TODOs](../specs/023-going-to-camp/TODO.md); see [the GoingToCamp plan](../specs/023-going-to-camp/plan.md).

## ReserveAmerica

`ReserveAmericaProvider` uses the public `a1.reserveamerica.com/jaxrs-json` API with the shared async retry/circuit breaker and one-request-per-second instance pacing. Provider ID **13** is seeded by migration. Run `task backend:migration-upgrade`, then `task backend:run -- camply db metadata --provider-id 13` to populate it.

Brand metadata supplies US state coverage; paginated state searches discover native, verifiable overnight campgrounds. External directory listings, day-use-only and hidden facilities are excluded. Campground IDs are `{contract}_{facility}`, and campsite IDs add `_{site}`. No artificial parent recreation areas are created. Complete discovery precedes the atomic campground/search transaction; stale campgrounds are disabled while references remain intact.

Site scans fetch every products page in 14-day grids and clip exact `AVAILABLE` daily statuses to the exclusive checkout boundary. A one-day `gal` triggered an upstream array-index server error during live verification, so even a one-night scan requests the full grid. Only `WEB_AVAILABLE`, nightly camping products qualify; phone-only bookings are excluded. Source capacity, electrical hookup and accessibility attributes map explicitly to the DTO, with raw attributes retained in metadata. Provider restrictions and minimum stays remain subject to the shared worker's existing limits.

Anonymous session setup uses the public search page and forwards optional `idToken`/`a1Data` headers when issued. An expired session refreshes once on 401; HTTP/schema/pagination errors propagate without publishing partial results. Pacing is per instance, not distributed. Live CO state discovery and a complete facility availability scan were verified on 2026-11-07. A later read-only crawl of all 50 US states validated 8,172 unique directory facilities, including 1,004 eligible campgrounds. Full-country database ingestion has not been exercised live. Additional NY and FLFS sample scans parsed successfully with no available sites on the selected night; their campground booking links resolved to HTTP 200. See [endpoint research and validation](../specs/024-reserve-america/validation.md).
