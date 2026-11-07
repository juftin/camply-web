"""Shared async GoingToCamp provider implementation.

Attributes
----------
_GRID_DAYS : int
    Maximum number of requested nights per map availability window.
_REQUEST_INTERVAL : float
    Minimum interval in seconds between requests within a provider instance.
"""

import asyncio
import time
from abc import ABC
from collections import defaultdict, deque
from datetime import date, timedelta
from typing import Any, ClassVar

import httpx2
import structlog
from pydantic import TypeAdapter
from sqlalchemy import update

from camply.db.config import db
from camply.db.models import Campground, Provider, RecreationArea
from camply.providers.base import BaseProvider
from camply.providers.dto import (
    CampgroundSearchResult,
    CampsiteDTO,
    ProviderSearchQuery,
    ProviderSearchResult,
    RecreationAreaSearchResult,
)
from camply.providers.going_to_camp.models.api import (
    AVAILABLE_STATUS,
    MAP_LINK_OPEN_STATUSES,
    AttributeDefinition,
    CatalogFilters,
    EquipmentCategory,
    MapAvailabilityResponse,
    Resource,
)
from camply.providers.going_to_camp.models.metadata import (
    BookingCategory,
    ResourceCategory,
    ResourceLocation,
    TransactionLocation,
    normalize_country_code,
    normalize_state_code,
    parse_gps_coordinates,
    resolve_overnight_categories,
)
from camply.providers.utils import normalize_name

logger = structlog.getLogger(__name__)

_GRID_DAYS = 60
_REQUEST_INTERVAL = 0.5


class GoingToCampProvider(BaseProvider, ABC):
    """Share async GoingToCamp availability scanning and catalog ingestion.

    Each GoingToCamp website assigns independent ``transactionLocationId`` and
    ``resourceLocationId`` sequences starting at ``-2147483648``, so every
    deployment is modeled as a concrete subclass with its own ``Provider`` ID.

    Attributes
    ----------
    api_url : str
        Complete GoingToCamp API root without a trailing slash.
    booking_url : str
        Public reservation web root without a trailing slash.
    state_code : str
        Two-letter state or province fallback for catalog rows.
    country_code : str
        Two-letter ISO country code fallback (``"US"`` by default).
    """

    api_url: ClassVar[str]
    booking_url: ClassVar[str]
    state_code: ClassVar[str]
    country_code: ClassVar[str] = "US"

    def __init__(self) -> None:
        """Reuse the base retry client and maintain per-instance pacing/caches."""
        super().__init__()
        self._request_lock = asyncio.Lock()
        self._last_request = 0.0
        self._filters: CatalogFilters | None = None

    async def _request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None
    ) -> httpx2.Response:
        """Perform paced async requests through the base retry transport."""
        async with self._request_lock:
            delay = _REQUEST_INTERVAL - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()
            response = await self.async_client.request(
                method,
                f"{self.api_url}/{path}",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response

    async def _ensure_filters(self) -> CatalogFilters:
        """Fetch and cache deployment categories, equipment, attributes, and locations."""
        if self._filters is None:
            locations_resp = await self._request("GET", "resourceLocation")
            booking_resp = await self._request("GET", "bookingcategories")
            resource_cat_resp = await self._request("GET", "resourcecategory")
            equipment_resp = await self._request("GET", "equipment")
            attributes_resp = await self._request("GET", "attribute/filterable")
            raw_attributes = attributes_resp.json()
            attribute_values = (
                list(raw_attributes.values())
                if isinstance(raw_attributes, dict)
                else raw_attributes
            )
            self._filters = CatalogFilters.build(
                resource_locations=TypeAdapter(list[ResourceLocation]).validate_python(
                    locations_resp.json()
                ),
                booking_categories=TypeAdapter(list[BookingCategory]).validate_python(
                    booking_resp.json()
                ),
                resource_categories=TypeAdapter(list[ResourceCategory]).validate_python(
                    resource_cat_resp.json()
                ),
                equipment_categories=TypeAdapter(
                    list[EquipmentCategory]
                ).validate_python(equipment_resp.json()),
                attributes=TypeAdapter(list[AttributeDefinition]).validate_python(
                    attribute_values
                ),
            )
        return self._filters

    async def _scan_booking_category_window(
        self,
        *,
        root_map_id: int,
        booking_category: BookingCategory,
        start_date: date,
        end_date: date,
        eligible_resources: dict[int, Resource],
        available_by_resource: dict[int, set[date]],
        booking_names_by_resource: dict[int, set[str]],
    ) -> None:
        """Traverse root and open child loop maps for one booking category and window."""
        nights_count = (end_date - start_date).days
        queue: deque[int] = deque([root_map_id])
        visited_maps: set[int] = set()
        while queue:
            map_id = queue.popleft()
            if map_id in visited_maps:
                continue
            visited_maps.add(map_id)
            response = await self._request(
                "GET",
                "availability/map",
                params={
                    "mapId": map_id,
                    "bookingCategoryId": booking_category.bookingCategoryId,
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "getDailyAvailability": "true",
                    "isReserving": "true",
                },
            )
            parsed = MapAvailabilityResponse.model_validate(response.json())
            for raw_res_id, entries in parsed.resourceAvailabilities.items():
                res_id = int(raw_res_id)
                if res_id not in eligible_resources:
                    continue
                for idx, entry in enumerate(entries[:nights_count]):
                    if entry.availability == AVAILABLE_STATUS:
                        available_by_resource[res_id].add(
                            start_date + timedelta(days=idx)
                        )
                        if booking_category.display_name:
                            booking_names_by_resource[res_id].add(
                                booking_category.display_name
                            )
            for raw_child_id, statuses in parsed.mapLinkAvailabilities.items():
                child_id = int(raw_child_id)
                if child_id not in visited_maps and any(
                    status in MAP_LINK_OPEN_STATUSES
                    for status in statuses[:nights_count]
                ):
                    queue.append(child_id)

    async def _load_facility_plan(
        self, resource_location_id: int, filters: CatalogFilters
    ) -> tuple[dict[int, Resource], list[BookingCategory]]:
        """Fetch eligible specific resources and matching overnight booking categories."""
        resources_resp = await self._request(
            "GET",
            "resourcelocation/resources",
            params={"resourceLocationId": resource_location_id},
        )
        raw_resources = TypeAdapter(dict[str, Resource]).validate_python(
            resources_resp.json()
        )
        eligible_resources = {
            res.resourceId: res
            for res in raw_resources.values()
            if res.is_eligible(filters) and res.resourceId is not None
        }
        facility_category_ids = {
            res.resourceCategoryId
            for res in eligible_resources.values()
            if res.resourceCategoryId is not None
        }
        relevant_booking = [
            filters.booking_categories[bc_id]
            for bc_id in sorted(filters.booking_categories)
            if set(filters.booking_categories[bc_id].allowedResourceCategoryIds)
            & facility_category_ids
        ]
        return eligible_resources, relevant_booking

    async def find_availabilities(
        self, park_id: str, start_date: date, end_date: date
    ) -> list[CampsiteDTO]:
        """Scan a resource location from arrival through the night before check-out."""
        if end_date <= start_date:
            raise ValueError("Check-out must be after arrival")
        try:
            resource_location_id = int(park_id)
        except ValueError as exc:
            raise ValueError(
                f"{self.provider.name} rejected the scan: invalid campground {park_id}"
            ) from exc

        filters = await self._ensure_filters()
        location = filters.resource_locations.get(resource_location_id)
        if location is None:
            raise ValueError(
                f"{self.provider.name} rejected the scan: unknown campground {park_id}"
            )
        if location.rootMapId is None:
            return []

        eligible_resources, relevant_booking = await self._load_facility_plan(
            resource_location_id, filters
        )
        if not eligible_resources or not relevant_booking:
            return []

        available_by_resource: dict[int, set[date]] = defaultdict(set)
        booking_names_by_resource: dict[int, set[str]] = defaultdict(set)
        current = start_date
        while current < end_date:
            window_end = min(current + timedelta(days=_GRID_DAYS), end_date)
            for booking_category in relevant_booking:
                await self._scan_booking_category_window(
                    root_map_id=location.rootMapId,
                    booking_category=booking_category,
                    start_date=current,
                    end_date=window_end,
                    eligible_resources=eligible_resources,
                    available_by_resource=available_by_resource,
                    booking_names_by_resource=booking_names_by_resource,
                )
            current = window_end

        return [
            dto
            for res_id, resource in eligible_resources.items()
            if res_id in available_by_resource
            and (
                dto := resource.to_dto(
                    filters=filters,
                    available_dates=available_by_resource[res_id],
                    booking_category_names=sorted(
                        booking_names_by_resource.get(res_id, ())
                    ),
                )
            )
            is not None
        ]

    async def search_upstream(
        self, query: ProviderSearchQuery
    ) -> list[ProviderSearchResult]:
        """Search fresh catalogs using the ingestion overnight eligibility rules."""
        response = await self._request("GET", "transactionlocation")
        parks = TypeAdapter(list[TransactionLocation]).validate_json(response.content)
        parents = {
            p.transactionLocationId: p
            for p in parks
            if p.display_name is not None and p.isDisabled is not True
        }
        results: list[ProviderSearchResult] = []
        if query.entity_type != "campground":
            results.extend(self._search_recreation_areas(query, parents))
        if query.entity_type == "recreation_area":
            return results
        response = await self._request("GET", "resourceLocation")
        facilities = TypeAdapter(list[ResourceLocation]).validate_json(response.content)
        response = await self._request("GET", "bookingcategories")
        bookings = TypeAdapter(list[BookingCategory]).validate_json(response.content)
        response = await self._request("GET", "resourcecategory")
        categories = TypeAdapter(list[ResourceCategory]).validate_json(response.content)
        _, overnight = resolve_overnight_categories(bookings, categories)
        for facility in facilities:
            if facility.transactionLocationId is None:
                continue
            park = parents.get(facility.transactionLocationId)
            if park is None or facility.display_name is None:
                continue
            row = self._build_campground_row(
                facility, parent_park=park, overnight_resource_ids=set(overnight)
            )
            if not row.reservable:
                continue
            result = CampgroundSearchResult(
                provider_id=self.provider.id,
                provider_name=self.provider.name,
                campground_id=row.id,
                campground_name=row.name,
                recreation_area_id=str(park.transactionLocationId),
                recreation_area_name=normalize_name(park.display_name),
                city=row.city,
                state=row.state,
                country=row.country,
                latitude=row.latitude,
                longitude=row.longitude,
                booking_url=self.get_campground_url(
                    row.id, rec_area_id=str(park.transactionLocationId)
                ),
            )
            if result.matches(query):
                results.append(result)
        return results

    def _search_recreation_areas(
        self,
        query: ProviderSearchQuery,
        parents: dict[int, TransactionLocation],
    ) -> list[ProviderSearchResult]:
        """Translate visible parks independently of campground matches."""
        results: list[ProviderSearchResult] = []
        for area in parents.values():
            row_area = self._build_park_row(area, has_overnight_campground=False)
            result_area = RecreationAreaSearchResult(
                provider_id=self.provider.id,
                provider_name=self.provider.name,
                recreation_area_id=row_area.id,
                recreation_area_name=row_area.name,
                city=row_area.city,
                state=row_area.state,
                country=row_area.country,
                latitude=row_area.latitude,
                longitude=row_area.longitude,
                booking_url=self.get_rec_area_url(row_area.id),
            )
            if result_area.matches(query):
                results.append(result_area)
        return results

    async def sync_metadata(self) -> None:
        """Refresh parks, campgrounds, and search rows using the ingestion workflow."""
        await self.populate_database()

    def _build_park_row(
        self, park: TransactionLocation, *, has_overnight_campground: bool
    ) -> RecreationArea:
        """Translate a ``TransactionLocation`` into a ``RecreationArea`` ORM row."""
        assert park.display_name is not None
        lat, lon = parse_gps_coordinates(park.gpsCoordinates)
        enabled = park.isDisabled is not True
        return RecreationArea(
            id=str(park.transactionLocationId),
            provider_id=self.provider.id,
            name=normalize_name(park.display_name),
            description=park.description,
            city=park.city,
            state=normalize_state_code(park.regionCode, self.state_code),
            country=self.country_code,
            latitude=lat,
            longitude=lon,
            reservable=enabled and has_overnight_campground,
            enabled=enabled,
        )

    def _build_campground_row(
        self,
        facility: ResourceLocation,
        *,
        parent_park: TransactionLocation,
        overnight_resource_ids: set[int],
    ) -> Campground:
        """Translate a ``ResourceLocation`` into a ``Campground`` ORM row."""
        assert facility.display_name is not None
        lat, lon = parse_gps_coordinates(facility.gpsCoordinates)
        if lat is None or lon is None:
            lat, lon = parse_gps_coordinates(parent_park.gpsCoordinates)
        enabled = parent_park.isDisabled is not True
        has_overnight = bool(set(facility.resourceCategoryIds) & overnight_resource_ids)
        return Campground(
            id=str(facility.resourceLocationId),
            provider_id=self.provider.id,
            recreation_area_id=str(parent_park.transactionLocationId),
            name=normalize_name(facility.display_name),
            description=facility.description,
            city=facility.city or parent_park.city,
            state=normalize_state_code(
                facility.region or parent_park.regionCode, self.state_code
            ),
            country=normalize_country_code(facility.country, self.country_code),
            latitude=lat,
            longitude=lon,
            reservable=enabled and facility.rootMapId is not None and has_overnight,
            enabled=enabled,
        )

    async def populate_database(self) -> None:
        """Fetch catalog endpoints before opening a transaction and upsert rows."""
        parks_resp = await self._request("GET", "transactionlocation")
        facilities_resp = await self._request("GET", "resourceLocation")
        booking_resp = await self._request("GET", "bookingcategories")
        resource_cat_resp = await self._request("GET", "resourcecategory")

        parks = TypeAdapter(list[TransactionLocation]).validate_python(
            parks_resp.json()
        )
        facilities = TypeAdapter(list[ResourceLocation]).validate_python(
            facilities_resp.json()
        )
        booking_categories = TypeAdapter(list[BookingCategory]).validate_python(
            booking_resp.json()
        )
        resource_categories = TypeAdapter(list[ResourceCategory]).validate_python(
            resource_cat_resp.json()
        )

        _, overnight_resources = resolve_overnight_categories(
            booking_categories, resource_categories
        )
        overnight_resource_ids = set(overnight_resources)
        parks_by_id = {
            park.transactionLocationId: park
            for park in parks
            if park.display_name is not None
        }
        valid_facilities = [
            fac
            for fac in facilities
            if fac.display_name is not None and fac.transactionLocationId in parks_by_id
        ]
        reservable_park_ids = {
            fac.transactionLocationId
            for fac in valid_facilities
            if fac.transactionLocationId is not None
            and fac.rootMapId is not None
            and bool(set(fac.resourceCategoryIds) & overnight_resource_ids)
        }

        async with db.get_session() as session:
            async with session.begin():
                if await session.get(Provider, self.provider.id) is None:
                    session.add(
                        Provider(
                            id=self.provider.id,
                            name=self.provider.name,
                            description=self.provider.description,
                            url=self.provider.url,
                            enabled=True,
                        )
                    )
                    await session.flush()
                await session.execute(
                    update(Campground)
                    .where(Campground.provider_id == self.provider.id)
                    .values(enabled=False, reservable=False)
                )
                await session.execute(
                    update(RecreationArea)
                    .where(RecreationArea.provider_id == self.provider.id)
                    .values(enabled=False, reservable=False)
                )
                for park in parks_by_id.values():
                    await session.merge(
                        self._build_park_row(
                            park,
                            has_overnight_campground=(
                                park.transactionLocationId in reservable_park_ids
                            ),
                        )
                    )
                await session.flush()
                for fac in valid_facilities:
                    assert fac.transactionLocationId is not None
                    await session.merge(
                        self._build_campground_row(
                            fac,
                            parent_park=parks_by_id[fac.transactionLocationId],
                            overnight_resource_ids=overnight_resource_ids,
                        )
                    )
                await session.flush()
                await self.populate_search_table(session)
        logger.info(
            "Refreshed GoingToCamp metadata",
            provider=self.provider.name,
            parks=len(parks_by_id),
            facilities=len(valid_facilities),
        )

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """Open a GoingToCamp park (`transactionLocationId`) in reservation search."""
        return (
            f"{cls.booking_url}/create-booking/results"
            f"?transactionLocationId={rec_area_id}"
        )

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """Open a GoingToCamp campground (`resourceLocationId`) in reservation search."""
        base = (
            f"{cls.booking_url}/create-booking/results"
            f"?resourceLocationId={campground_id}"
        )
        if rec_area_id is None:
            return base
        return f"{base}&transactionLocationId={rec_area_id}"
