# DESIGN_PROVIDERS: Provider Architecture & Logic Migration

This document outlines the architecture for the provider layer in `camply`, focusing on a standardized interface, provider-specific Pydantic models, and the logic migration from the legacy CLI.

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
_Example_: `backend/packages/providers/recreation_gov/models/api.py`.

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

- **Connection Pooling**: Use a shared `httpx.AsyncClient` within the provider package.
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

Apply the provider seed migration with `task backend:migration-upgrade`. With Celery Beat and a worker running, ingestion refreshes registered providers daily at midnight UTC. Worker startup does not currently trigger ingestion. For a manual refresh, run `task backend:run -- populate-database --provider-id 2` (the CLI defaults to Recreation.gov for compatibility).

Metadata ingestion is independent of availability scans and requires no campground selection or date range. `sync_metadata()` delegates to `populate_database()`, fetching the complete parks and facilities catalogs and updating `providers`, `recreation_areas`, `campgrounds`, and `search`. Nameless entries and facilities without a known parent park are omitted. Hidden and offline records are retained in metadata with their visibility/bookability flags; searchable campgrounds must be enabled and reservable. Individual campsite/unit metadata and filter dictionaries are not persisted: the current schema has no `campsites` table, and those details are parsed when scanning availability.

Regression tests use generated synthetic responses, including a VCR replay with request-body matching through the real retry transport. Public metadata and availability endpoints were also verified live on 2026-10-12; live responses and reservation identifiers are not stored in test fixtures. See [the feature plan](../../specs/004-reserve-california/plan.md).

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

Apply migrations with `task backend:migration-upgrade`, then populate any provider with `task backend:run -- populate-database --provider-id 3` (Florida in this example). `task backend:run -- populate-database --help` lists every registered ID. The existing ingestion orchestrator fans out all registered providers and Celery Beat schedules it daily at midnight UTC. Initial population remains manual; worker startup does not trigger it.

On 2026-10-12, all nine added providers responded to park/facility catalogs, filters, sample overnight grids, and public booking-page checks. API roots and booking hosts are fixed in each concrete variation; Virginia uses a Tyler host, and Ohio/Missouri use their current reservation hosts. Regional providers keep the CLI's search-page fallback until facility deep links are separately verified.

Alabama State Parks and Maricopa County's legacy catalog endpoints returned HTTP 404. They are not registered or seeded. See [UseDirect TODOs](../../specs/005-usedirect-providers/TODO.md) for endpoint discovery and other known limits, and [the implementation plan](../../specs/005-usedirect-providers/plan.md) for scope and verification. Shared worker minimum stays, residency-aware booking windows, cross-worker rate limiting, and individual campsite persistence remain follow-ups.
