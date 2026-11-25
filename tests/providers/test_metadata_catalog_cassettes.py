"""Verify catalog sync and campsite listing against recorded metadata."""

from datetime import datetime, timezone, tzinfo
from pathlib import Path
from unittest.mock import AsyncMock

import httpx2
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from camply.db.models import Campground, RecreationArea, Search
from camply.providers import PROVIDERS
from camply.providers.dto import CampsiteType
from camply.providers.reserve_america.models.api import Facility
from tests.providers.metadata_cases import TARGETS, MetadataTarget
from tests.providers.metadata_replay import metadata_replay, stage_ridb

EXPECTED_SITES = {
    "recreation-gov": ("103904", "001", 35, False, False),
    "usedirect": ("4245", "Campsite #53", 20, False, False),
    "going-to-camp": ("-2147481558", "31", 42, True, True),
    "reserve-america": ("CO_50021_3134", "001", 50, True, False),
}


class BrowseClock(datetime):
    """Make provider listings query the recorded December 7 browse date."""

    @classmethod
    def now(cls, tz: tzinfo | None = None) -> datetime:
        """Return December 6 for adapters that browse tomorrow's grid."""
        instant = datetime(2026, 12, 6, 12, tzinfo=timezone.utc)
        return instant.replace(tzinfo=None) if tz is None else instant.astimezone(tz)


@pytest.mark.anyio
@pytest.mark.parametrize("case", TARGETS, ids=lambda case: case.key)
async def test_metadata_catalog(
    case: MetadataTarget,
    pytestconfig: pytest.Config,
    metadata_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Replay catalog persistence and exact site capability mapping."""
    if case.family == "recreation-gov":
        stage_ridb(tmp_path, monkeypatch, config=pytestconfig)
    elif case.family == "usedirect":
        monkeypatch.setattr("camply.providers.usedirect.provider.datetime", BrowseClock)
    elif case.family == "reserve-america":
        monkeypatch.setattr(
            "camply.providers.reserve_america.provider.datetime", BrowseClock
        )

    provider = PROVIDERS[case.provider_id]()
    try:
        with metadata_replay(pytestconfig, operation="catalog", case=case):
            if case.family == "reserve-america" and pytestconfig.getoption(
                "record_provider_metadata"
            ):
                # Stage the selected state without crawling the entire national catalog.
                await provider._request("config/brand", {"brandName": "RA"})
                await provider._pages(
                    "search",
                    {"stype": "state", "tstc": case.state, "interest": "camping"},
                    Facility,
                )
            else:
                await provider.sync_metadata()
                await _assert_persisted_catalog(metadata_database, case=case)
            sites = await provider.list_campsites(case.campground_id)
            site_id, name, length, electric, accessible = EXPECTED_SITES[case.family]
            site = next(
                candidate for candidate in sites if candidate.campsite_id == site_id
            )
            assert site.campsite_name == name
            assert site.campsite_type == CampsiteType.RV
            assert (site.max_vehicle_length, site.is_electric, site.is_accessible) == (
                length,
                electric,
                accessible,
            )
            assert site.available_dates == []

        if case.family == "usedirect":
            incomplete = AsyncMock(
                return_value=httpx2.Response(200, json={"Message": "Incomplete"})
            )
            monkeypatch.setattr(provider, "_request", incomplete)
            with pytest.raises(ValidationError):
                await provider.sync_metadata()
            incomplete.assert_awaited_once()
            await _assert_persisted_catalog(metadata_database, case=case)
    finally:
        await provider.async_client.aclose()


async def _assert_persisted_catalog(
    maker: async_sessionmaker[AsyncSession], *, case: MetadataTarget
) -> None:
    """Verify normalized rows and the searchable campground relationship."""
    async with maker() as session:
        campground = await session.get(
            Campground, (case.campground_id, case.provider_id)
        )
        assert campground is not None and campground.enabled and campground.reservable
        assert campground.recreation_area_id == case.area_id
        assert campground.name.casefold() == case.campground_name.casefold()
        if case.area_id is not None:
            area = await session.get(RecreationArea, (case.area_id, case.provider_id))
            assert area is not None and area.enabled
        search = await session.scalar(
            select(Search).where(
                Search.provider_id == case.provider_id,
                Search.campground_id == case.campground_id,
            )
        )
        assert search is not None
        assert search.recreation_area_id == case.area_id
        assert search.campground_name == campground.name
