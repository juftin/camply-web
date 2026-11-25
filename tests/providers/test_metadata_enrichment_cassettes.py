"""Verify provider enrichment snapshots with public recorded source data."""

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import httpx2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from camply.db.models import Campground, RecreationArea
from camply.providers import PROVIDERS
from tests.providers.metadata_cases import ENRICHMENT_TARGETS, MetadataTarget
from tests.providers.metadata_replay import metadata_replay, stage_ridb

PHOTO_URLS = {
    "recreation-gov": "https://cdn.recreation.gov/public/2018/09/13/22/02/272300_ff4212be-f15c-4653-9e9c-13b2d042a0d9_1440.webp",
    "usedirect": "https://azstateparks.com/reserve/images/Arizona/ParkImages/Place/13.jpg",
    "reserve-america": "https://a1.reserveamerica.com/webphotos/originals/CO/pid50028/%7Bpht%7D540x360%7Bpht%7D1454464587412.jpg",
}
JOSHUA_TREE_PHOTO = (
    "https://cdn.recreation.gov/public/2021/05/09/15/00/"
    "2782_a8f41e32-d02d-491e-8e07-20f02d583f74.jpeg"
)


@pytest.mark.anyio
@pytest.mark.parametrize("case", ENRICHMENT_TARGETS, ids=lambda case: case.key)
async def test_metadata_enrichment(
    case: MetadataTarget,
    pytestconfig: pytest.Config,
    metadata_database: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Refresh selected identities and verify their own practical information."""
    async with metadata_database.begin() as session:
        if case.area_id is not None:
            session.add(
                RecreationArea(
                    id=case.area_id,
                    provider_id=case.provider_id,
                    name=case.area_name,
                    enabled=True,
                    reservable=True,
                )
            )
            await session.flush()
        session.add(
            Campground(
                id=case.campground_id,
                provider_id=case.provider_id,
                name=case.campground_name,
                recreation_area_id=case.area_id,
                enabled=True,
                reservable=True,
            )
        )

    if case.family == "recreation-gov":
        stage_ridb(tmp_path, monkeypatch, config=pytestconfig)
        replay = nullcontext()
    else:
        replay = metadata_replay(pytestconfig, operation="enrichment", case=case)

    provider = PROVIDERS[case.provider_id]()
    try:
        with replay:
            await provider.enrich_metadata()
            async with metadata_database() as session:
                campground = await session.get(
                    Campground, (case.campground_id, case.provider_id)
                )
                assert campground is not None and campground.details is not None
                details = campground.details
                if case.area_id is None:
                    assert PHOTO_URLS[case.family] in {
                        photo["url"] for photo in details["photos"]
                    }
                    assert "Beach (Swimming)" in details["amenities"]
                    return
                area = await session.get(
                    RecreationArea, (case.area_id, case.provider_id)
                )
                assert area is not None and area.details is not None
                area_details = area.details

            if case.family == "recreation-gov":
                assert PHOTO_URLS[case.family] in {
                    photo["url"] for photo in details["photos"]
                }
                assert JOSHUA_TREE_PHOTO in {
                    photo["url"] for photo in area_details["photos"]
                }
                assert JOSHUA_TREE_PHOTO not in {
                    photo["url"] for photo in details["photos"]
                }
                assert details["directions"] and area_details["directions"]
            else:
                assert PHOTO_URLS["usedirect"] in {
                    photo["url"] for photo in area_details["photos"]
                }
                assert {
                    "label": "Park office",
                    "value": "6 a.m. to 8 p.m. daily",
                } in area_details["hours"]
                assert details["photos"] == [] and details["hours"] == []
        if case.family == "usedirect":
            async with metadata_database.begin() as session:
                area = await session.get(
                    RecreationArea, (case.area_id, case.provider_id)
                )
                area.details = {
                    **area_details,
                    "fetched_at": (
                        datetime.now(timezone.utc) - timedelta(days=8)
                    ).isoformat(),
                }
                area.details_attempted_at = None
                original = area.details
            incomplete = AsyncMock(
                return_value=httpx2.Response(200, json={"PlaceId": 13})
            )
            monkeypatch.setattr(provider, "_request", incomplete)
            await provider.enrich_metadata()
            incomplete.assert_awaited_once()
            async with metadata_database() as session:
                area = await session.get(
                    RecreationArea, (case.area_id, case.provider_id)
                )
                assert area.details == original
    finally:
        await provider.async_client.aclose()
