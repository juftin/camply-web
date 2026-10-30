"""Shared async UseDirect / Tyler RDR provider implementation.

Attributes
----------
_GRID_DAYS : int
    Maximum number of requested nights per availability grid.
_REQUEST_INTERVAL : float
    Minimum interval between requests within a provider instance.
_STATE_CODE_LENGTH : int
    Length of a normalized state or territory code.
"""

import asyncio
import time
from abc import ABC
from datetime import date, timedelta
from typing import Any, ClassVar

import httpx
import structlog
from pydantic import TypeAdapter
from sqlalchemy import update

from camply.db.config import db
from camply.db.models import Campground, Provider, RecreationArea
from camply.providers.base import BaseProvider
from camply.providers.dto import CampsiteDTO
from camply.providers.usedirect.models.api import AvailabilityResponse, SearchFilters
from camply.providers.usedirect.models.metadata import Facility, Place
from camply.providers.utils import normalize_name

logger = structlog.getLogger(__name__)

_GRID_DAYS = 30
_REQUEST_INTERVAL = 1.0
_STATE_CODE_LENGTH = 2


class UseDirectProvider(BaseProvider, ABC):
    """Share async RDR scanning and independent catalog ingestion.

    Subclasses supply the inherited abstract provider identity and these
    deployment attributes. Booking methods may be overridden for different
    application routes, such as California's modern park/facility paths.

    Attributes
    ----------
    api_url : str
        Complete RDR API root, including the deployment-specific path.
    booking_url : str
        Public booking application root without a trailing slash.
    state_code : str
        Two-letter state or territory fallback for catalog locations.
    country_code : str
        ISO country code; US by default and AU for Northern Territory.
    booking_path_params : bool
        Whether the booking application accepts hash-based park routes.
    """

    api_url: ClassVar[str]
    booking_url: ClassVar[str]
    state_code: ClassVar[str]
    country_code: ClassVar[str] = "US"
    booking_path_params: ClassVar[bool] = True

    def __init__(self) -> None:
        """Reuse the base retry client and pace provider requests."""
        super().__init__()
        self._request_lock = asyncio.Lock()
        self._last_request = 0.0
        self._filters: SearchFilters | None = None

    async def _request(
        self, method: str, path: str, *, payload: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Perform paced async requests through the base retry transport."""
        async with self._request_lock:
            delay = _REQUEST_INTERVAL - (time.monotonic() - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()
            response = await self.async_client.request(
                method, f"{self.api_url}/{path}", json=payload, timeout=30.0
            )
            response.raise_for_status()
            return response

    async def find_availabilities(
        self, park_id: str, start_date: date, end_date: date
    ) -> list[CampsiteDTO]:
        """Scan a facility from arrival through the night before check-out.

        The grid endpoint uses inclusive dates and sometimes pads its
        response beyond the requested interval. Each response is clipped
        to its requested window before merging real UnitIds.
        """
        if end_date <= start_date:
            raise ValueError("Check-out must be after arrival")
        facility_id = int(park_id)
        if self._filters is None:
            response = await self._request("GET", "search/filters")
            self._filters = SearchFilters.model_validate(response.json())
        campsites: dict[str, CampsiteDTO] = {}
        current = start_date
        while current < end_date:
            window_end = min(current + timedelta(days=_GRID_DAYS), end_date)
            response = await self._request(
                "POST",
                "search/grid",
                payload={
                    "FacilityId": facility_id,
                    "StartDate": current.strftime("%m-%d-%Y"),
                    "EndDate": (window_end - timedelta(days=1)).strftime("%m-%d-%Y"),
                    "WebOnly": True,
                    "InSeasonOnly": True,
                    "UnitSort": "orderby",
                },
            )
            parsed = AvailabilityResponse.model_validate(response.json())
            if parsed.NightsActual == 0:
                raise ValueError(
                    f"{self.provider.name} rejected the scan: {parsed.Message}"
                )
            facility = parsed.Facility
            if facility is not None:
                if facility.FacilityId != facility_id:
                    raise ValueError(
                        f"{self.provider.name} returned a different facility"
                    )
                for dto in facility.to_dtos(
                    filters=self._filters, start_date=current, end_date=window_end
                ):
                    if dto.campsite_id in campsites:
                        existing = campsites[dto.campsite_id]
                        existing.available_dates = sorted(
                            set(existing.available_dates + dto.available_dates)
                        )
                        existing.metadata["minimum_stays"].update(
                            dto.metadata["minimum_stays"]
                        )
                    else:
                        campsites[dto.campsite_id] = dto
            current = window_end
        return list(campsites.values())

    async def sync_metadata(self) -> None:
        """Refresh parks, campgrounds, and search using the ingestion workflow."""
        await self.populate_database()

    async def populate_database(self) -> None:
        """Fetch metadata before opening a transaction and upsert provider rows."""
        places_response = await self._request("GET", "fd/places")
        places: list[Place] = TypeAdapter(list[Place]).validate_python(
            places_response.json()
        )
        facilities_response = await self._request("GET", "fd/facilities")
        facilities: list[Facility] = TypeAdapter(list[Facility]).validate_python(
            facilities_response.json()
        )
        places_by_id = {p.PlaceId: p for p in places if p.Name and p.Name.strip()}
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
                for place in places_by_id.values():
                    await session.merge(
                        RecreationArea(
                            id=str(place.PlaceId),
                            provider_id=self.provider.id,
                            name=normalize_name(place.Name),
                            description=place.Description,
                            city=place.City,
                            state=self._metadata_state(place),
                            country=self.country_code,
                            longitude=place.Longitude,
                            latitude=place.Latitude,
                            reservable=place.AllowWebBooking is True
                            and place.IsWebViewable is not False,
                            enabled=place.IsWebViewable is not False,
                        )
                    )
                await session.flush()
                for facility in facilities:
                    parent_place = places_by_id.get(facility.PlaceId)
                    if (
                        parent_place is None
                        or not facility.Name
                        or not facility.Name.strip()
                    ):
                        continue
                    await session.merge(
                        Campground(
                            id=str(facility.FacilityId),
                            provider_id=self.provider.id,
                            recreation_area_id=str(facility.PlaceId),
                            name=normalize_name(facility.Name),
                            description=facility.Description,
                            city=parent_place.City,
                            state=self._metadata_state(parent_place),
                            country=self.country_code,
                            longitude=parent_place.Longitude,
                            latitude=parent_place.Latitude,
                            reservable=facility.AllowWebBooking is True
                            and parent_place.AllowWebBooking is True
                            and parent_place.IsWebViewable is not False,
                            enabled=parent_place.IsWebViewable is not False,
                        )
                    )
                await session.flush()
                await self.populate_search_table(session)
        logger.info(
            "Refreshed UseDirect metadata",
            provider=self.provider.name,
            parks=len(places_by_id),
            facilities=len(facilities),
        )

    @classmethod
    def _metadata_state(cls, place: Place) -> str:
        """Normalize state codes, using the deployment fallback for missing names."""
        state = (place.State or "").strip().upper()
        return state if len(state) == _STATE_CODE_LENGTH else cls.state_code

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """Open a park when hash routes are supported; otherwise open search."""
        if not cls.booking_path_params:
            return cls.booking_url
        return f"{cls.booking_url}/#!park/{rec_area_id}"

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """Open a facility with park context when supported by the booking app."""
        if rec_area_id is None or not cls.booking_path_params:
            return cls.booking_url
        return f"{cls.booking_url}/#!park/{rec_area_id}/{campground_id}"
