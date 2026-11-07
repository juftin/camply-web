"""Async ReserveAmerica catalog ingestion and site availability scanning.

Attributes
----------
_REQUEST_INTERVAL : float
    Minimum per-instance interval between public requests in seconds.
_GRID_DAYS : int
    Public frontend's availability window length.
"""

import asyncio
import time
from datetime import date, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any, ClassVar, TypeVar
from urllib.parse import unquote, urlencode

import httpx2
from sqlalchemy import update

from camply.db.config import db
from camply.db.data.providers import ReserveAmerica
from camply.db.models import Campground, Provider
from camply.providers.base import BaseProvider
from camply.providers.dto import CampsiteDTO
from camply.providers.reserve_america.models.api import (
    BrandCatalog,
    Facility,
    Page,
    Site,
    split_facility_id,
)
from camply.providers.utils import normalize_name

_REQUEST_INTERVAL = 1.0
_GRID_DAYS = 14
_MAX_PAGES = 10000
_Record = TypeVar("_Record", Facility, Site)


class ReserveAmericaProvider(BaseProvider):
    """Use ReserveAmerica's public same-origin API without account credentials."""

    api_url: ClassVar[str] = "https://a1.reserveamerica.com/jaxrs-json"
    session_url: ClassVar[str] = "https://a1.reserveamerica.com/explore/search-results"
    booking_url: ClassVar[str] = "https://www.reserveamerica.com"

    def __init__(self) -> None:
        """Reuse retry/circuit-breaker transport and serialize anonymous session setup."""
        super().__init__()
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._session_ready = False

    @property
    def provider(self) -> Provider:
        """Return the permanent provider identity."""
        return ReserveAmerica

    async def _get(self, url: str, **kwargs: Any) -> httpx2.Response:
        """Pace every HTTP operation, including session bootstrap."""
        delay = _REQUEST_INTERVAL - (time.monotonic() - self._last_request)
        if delay > 0:
            await asyncio.sleep(delay)
        self._last_request = time.monotonic()
        return await self.async_client.get(url, timeout=30.0, **kwargs)

    async def _bootstrap(self) -> None:
        """Establish anonymous cookies and optional upstream token headers."""
        self._session_ready = False
        self.async_client.cookies.clear()
        response = await self._get(self.session_url, follow_redirects=True)
        response.raise_for_status()
        self._session_ready = True

    def _cookie_auth_headers(self, url: str) -> dict[str, str]:
        """Mirror current, unexpired cookies applicable to this request URL only."""
        request = self.async_client.build_request("GET", url)
        headers: dict[str, str] = {}
        # The client sends longer paths first. Keep the first matching token;
        # parsing the whole header would replace it with an older root cookie.
        for part in request.headers.get("Cookie", "").split(";"):
            cookie = SimpleCookie()
            cookie.load(part.strip())
            if token := cookie.get("idToken"):
                headers.setdefault("Authorization", token.value)
            if a1_data := cookie.get("a1Data"):
                headers.setdefault("A1Data", unquote(a1_data.value))
        return headers

    async def _request(self, path: str, params: dict[str, Any]) -> Any:
        """Refresh an expired session once; never swallow HTTP or JSON errors."""
        async with self._lock:
            if not self._session_ready:
                await self._bootstrap()
            url = f"{self.api_url}/{path}"
            response = await self._get(
                url, params=params, headers=self._cookie_auth_headers(url)
            )
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                await self._bootstrap()
                response = await self._get(
                    url, params=params, headers=self._cookie_auth_headers(url)
                )
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                self._session_ready = False
            response.raise_for_status()
            return response.json()

    async def _pages(
        self, path: str, params: dict[str, Any], model: type[_Record]
    ) -> list[_Record]:
        """Validate all pages before returning any records to persistence or polling."""
        records: list[_Record] = []
        page_number = 0
        expected_total: int | None = None
        while True:
            raw = await self._request(path, {**params, "rcp": page_number, "rcs": 50})
            page = Page[dict[str, Any]].model_validate(raw)
            if page.control.currentPage != page_number:
                raise ValueError("ReserveAmerica returned an unexpected page")
            if expected_total is None:
                expected_total = page.totalRecords
            if page.totalRecords != expected_total:
                raise ValueError("ReserveAmerica catalog changed during pagination")
            records.extend(model.model_validate(record) for record in page.records)
            if page_number >= page.totalPages - 1:
                if len(records) != expected_total:
                    raise ValueError("ReserveAmerica returned incomplete records")
                return records
            if not page.records or page_number >= _MAX_PAGES:
                raise ValueError("ReserveAmerica pagination made no progress")
            page_number += 1

    async def find_availabilities(
        self, park_id: str, start_date: date, end_date: date
    ) -> list[CampsiteDTO]:
        """Aggregate nightly site grids over bounded windows with exclusive check-out."""
        contract, facility = split_facility_id(park_id)
        if end_date <= start_date:
            raise ValueError("Check-out must be after arrival")
        sites: dict[int, Site] = {}
        dates: dict[int, set[date]] = {}
        current = start_date
        while current < end_date:
            window_end = min(current + timedelta(days=_GRID_DAYS), end_date)
            records = await self._pages(
                f"products/{contract}/{facility}",
                {"gad": current.isoformat(), "gal": _GRID_DAYS},
                Site,
            )
            for site in records:
                if not site.eligible:
                    continue
                nights = {
                    n.date
                    for n in site.availabilityGrid
                    if n.status == "AVAILABLE" and current <= n.date < window_end
                }
                if nights:
                    sites[site.id] = site
                    dates.setdefault(site.id, set()).update(nights)
            current = window_end
        return [
            site.to_dto(
                park_id,
                dates[key],
                f"{self.booking_url}/campsiteDetails.do?{urlencode({'contractCode': contract, 'parkId': facility, 'siteId': key})}",
            )
            for key, site in sites.items()
        ]

    async def sync_metadata(self) -> None:
        """Refresh the public catalog independently of scan selections."""
        await self.populate_database()

    async def populate_database(self) -> None:
        """Fetch the complete catalog first, then refresh metadata/search atomically."""
        facilities: dict[str, Facility] = {}
        catalog = BrandCatalog.model_validate(
            await self._request("config/brand", {"brandName": "RA"})
        )
        states = sorted({s.stateCode for s in catalog.states if s.countryCode == "USA"})
        if not states:
            raise ValueError("ReserveAmerica returned no US catalog states")
        for state in states:
            records = await self._pages(
                "search",
                {"stype": "state", "tstc": state, "interest": "camping"},
                Facility,
            )
            facilities.update({f.key: f for f in records if f.eligible})
        if not facilities:
            raise ValueError("ReserveAmerica returned no native overnight facilities")
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
                for key, facility in facilities.items():
                    d = facility.details
                    await session.merge(
                        Campground(
                            id=key,
                            provider_id=self.provider.id,
                            name=normalize_name(facility.name),
                            description=d.description,
                            state=next(iter(d.stateCodes), None),
                            country="US",
                            latitude=d.coordinates.latitude if d.coordinates else None,
                            longitude=d.coordinates.longitude
                            if d.coordinates
                            else None,
                            enabled=True,
                            reservable=True,
                        )
                    )
                await session.flush()
                await self.populate_search_table(session)

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """Open a facility (there is no synthetic parent park identity)."""
        return cls.get_campground_url(rec_area_id)

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """Build a contract-aware reservation URL."""
        contract, facility = split_facility_id(campground_id)
        return f"{cls.booking_url}/campgroundDetails.do?{urlencode({'contractCode': contract, 'parkId': facility})}"
