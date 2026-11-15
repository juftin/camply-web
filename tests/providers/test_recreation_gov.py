"""
Tests for Recreation.gov Provider
"""

import datetime
from unittest.mock import AsyncMock, patch

import pytest

from camply.providers.dto import CampsiteType
from camply.providers.recreation_gov.provider import (
    RecreationGovProvider,
    check_is_electric,
    map_campsite_type,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_map_campsite_type():
    """
    Test that campsite type strings are parsed correctly into standardized enums.
    """
    assert map_campsite_type("Standard Tent Only") == CampsiteType.TENT
    assert map_campsite_type("Tent Only Nonelectric") == CampsiteType.TENT
    assert map_campsite_type("RV Electric") == CampsiteType.RV
    assert map_campsite_type("RV Nonelectric") == CampsiteType.RV
    assert map_campsite_type("Cabin") == CampsiteType.CABIN
    assert map_campsite_type("Yurt") == CampsiteType.CABIN
    assert map_campsite_type("Group Picnic Area") == CampsiteType.OTHER
    assert map_campsite_type(None) == CampsiteType.OTHER


def test_check_is_electric():
    """
    Test electric hookup checking logic from attributes and type.
    """
    from camply.providers.recreation_gov.models.api import (
        RecDotGovAttribute,
        RecDotGovCampsite,
    )

    # 1. Electric in type
    campsite_with_type = RecDotGovCampsite(
        campsite_id=1,
        name="1",
        type="Electric RV",
    )
    assert check_is_electric(campsite_with_type) is True

    # 2. Electric in attributes
    campsite_with_attr = RecDotGovCampsite(
        campsite_id=2,
        name="2",
        attributes=[
            RecDotGovAttribute(
                attribute_id=1,
                attribute_name="Electricity Hookup",
                attribute_value="50 Amp",
            )
        ],
    )
    assert check_is_electric(campsite_with_attr) is True

    # 3. Not electric
    campsite_non_electric = RecDotGovCampsite(
        campsite_id=3,
        name="3",
        attributes=[
            RecDotGovAttribute(
                attribute_id=1,
                attribute_name="Electricity Hookup",
                attribute_value="No",
            )
        ],
    )
    assert check_is_electric(campsite_non_electric) is False


@pytest.mark.vcr
@pytest.mark.anyio
async def test_find_availabilities():
    """
    Test the complete async find_availabilities flow using VCRPy recorded HTTP requests.
    """
    provider = RecreationGovProvider()

    # We will query Apache Trout Campground (facility ID 234708)
    # for a specific date range that we record/replay.
    start_date = datetime.date(2026, 9, 1)
    end_date = datetime.date(2026, 9, 2)

    availabilities = await provider.find_availabilities(
        park_id="234708",
        start_date=start_date,
        end_date=end_date,
    )

    # Structural assertions to verify that data is loaded and mapped correctly
    assert isinstance(availabilities, list)
    # Check that we successfully fetch and map to DTOs
    for avail in availabilities:
        assert avail.campsite_id
        assert avail.campsite_name
        assert avail.campsite_type in CampsiteType
        assert isinstance(avail.available_dates, list)
        assert len(avail.available_dates) > 0
        assert all(start_date <= d <= end_date for d in avail.available_dates)


@pytest.mark.anyio
async def test_sync_metadata():
    """
    Test that sync_metadata calls populate_database.
    """
    provider = RecreationGovProvider()
    with patch.object(
        provider, "populate_database", new_callable=AsyncMock
    ) as mock_populate:
        await provider.sync_metadata()
        mock_populate.assert_called_once()


@pytest.mark.anyio
async def test_recreation_gov_populate_fails_without_provider_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider metadata refresh must fail if the database record is missing."""
    from types import SimpleNamespace

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from camply.db.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "camply.providers.recreation_gov.provider.db",
        SimpleNamespace(get_session=maker),
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    provider = RecreationGovProvider()
    try:
        with pytest.raises(RuntimeError, match=r"Provider .* not found in database"):
            await provider.populate_database()
    finally:
        await provider.async_client.aclose()
        await engine.dispose()


def _build_synthetic_catalog(today: datetime.date) -> tuple[object, object, object]:
    """Build synthetic valid area, campground, and empty campground payloads."""
    from camply.providers.recreation_gov.models.campgrounds import (
        RecDotGovCampground,
        RecDotGovCampgroundData,
    )
    from camply.providers.recreation_gov.models.recreation_area import (
        RecDotGovRecreationArea,
        RecDotGovRecreationAreaData,
    )

    valid_areas = RecDotGovRecreationAreaData(
        RECDATA=[
            RecDotGovRecreationArea(
                RecAreaID="area-1",
                OrgRecAreaID=None,
                ParentOrgID=None,
                RecAreaName="Valid Area",
                RecAreaDescription="Desc",
                RecAreaLongitude=-119.5,
                RecAreaLatitude=37.7,
                Reservable=True,
                Enabled=True,
                LastUpdatedDate=today,
            ),
            RecDotGovRecreationArea(
                RecAreaID="nameless",
                OrgRecAreaID=None,
                ParentOrgID=None,
                RecAreaName="",
                RecAreaDescription=None,
                RecAreaLongitude=-119.5,
                RecAreaLatitude=37.7,
                Reservable=True,
                Enabled=True,
                LastUpdatedDate=today,
            ),
        ]
    )
    valid_cgs = RecDotGovCampgroundData(
        RECDATA=[
            RecDotGovCampground(
                FacilityID="cg-1",
                ParentRecAreaID="area-1",
                FacilityName="Valid CG",
                FacilityDescription="Desc",
                FacilityTypeDescription="Campground",
                FacilityLongitude=-119.5,
                FacilityLatitude=37.7,
                Reservable=True,
                Enabled=True,
            )
        ]
    )
    return valid_areas, valid_cgs, RecDotGovCampgroundData(RECDATA=[])


async def _setup_atomic_catalog_db(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[object, object]:
    """Create an isolated SQLite DB seeded with stale area and campground rows."""
    from types import SimpleNamespace

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from camply.db.models import Base, Campground, Provider, RecreationArea

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "camply.providers.recreation_gov.provider.db",
        SimpleNamespace(get_session=maker),
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with maker() as session:
        session.add(Provider(id=1, name="Recreation.gov", url="https://recreation.gov"))
        session.add(RecreationArea(id="stale-area", provider_id=1, name="Stale Area"))
        session.add(
            Campground(
                id="stale-cg",
                provider_id=1,
                recreation_area_id="stale-area",
                name="Stale CG",
            )
        )
        await session.commit()
    return engine, maker


@pytest.mark.anyio
async def test_recreation_gov_atomic_catalog_sync_and_enrichment_isolation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: datetime.date | object
) -> None:
    """Reject partial datasets cleanly, soft-disable removed rows, and isolate enrichment failures."""
    from pathlib import Path

    from sqlalchemy import select

    from camply.db.models import Campground, Provider, RecreationArea

    assert isinstance(tmp_path, Path)
    engine, maker = await _setup_atomic_catalog_db(monkeypatch)

    provider = RecreationGovProvider()
    archive = tmp_path / "ridb.zip"
    archive.write_bytes(b"synthetic")
    monkeypatch.setattr(
        provider, "download_offline_data", AsyncMock(return_value=archive)
    )
    valid_areas, valid_cgs, empty_cgs = _build_synthetic_catalog(
        datetime.date(2027, 7, 1)
    )

    def fake_read(_path: Path, data: object) -> object:
        return (
            valid_areas
            if getattr(data, "json_file", "").startswith("RecAreas")
            else empty_cgs
        )

    monkeypatch.setattr(
        "camply.providers.recreation_gov.provider._read_catalog", fake_read
    )
    try:
        with pytest.raises(ValueError, match=r"Incomplete Recreation\.gov catalog"):
            await provider.populate_database()
        async with maker() as session:
            assert (await session.get(Provider, 1)).catalog_revision == 0
            assert (await session.get(Campground, ("stale-cg", 1))).enabled is True

        def fake_read_complete(_path: Path, data: object) -> object:
            return (
                valid_areas
                if getattr(data, "json_file", "").startswith("RecAreas")
                else valid_cgs
            )

        monkeypatch.setattr(
            "camply.providers.recreation_gov.provider._read_catalog",
            fake_read_complete,
        )
        await provider.populate_database()
        async with maker() as session:
            assert (await session.get(Provider, 1)).catalog_revision == 1
            stale_cg = await session.get(Campground, ("stale-cg", 1))
            stale_area = await session.get(RecreationArea, ("stale-area", 1))
            assert stale_cg is not None and stale_cg.enabled is False
            assert stale_area is not None and stale_area.enabled is False
            assert (await session.get(RecreationArea, ("nameless", 1))) is None
            areas = (await session.scalars(select(RecreationArea))).all()
            assert any(area.id == "area-1" and area.enabled for area in areas)

        monkeypatch.setattr(
            provider,
            "enrich_metadata",
            AsyncMock(side_effect=RuntimeError("enrichment failed")),
        )
        with pytest.raises(RuntimeError, match="enrichment failed"):
            await provider.enrich_metadata()
        async with maker() as session:
            assert (await session.get(Provider, 1)).catalog_revision == 1
            assert (await session.get(Campground, ("cg-1", 1))).enabled is True
    finally:
        await provider.async_client.aclose()
        await engine.dispose()
