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


def _write_ridb_zip(archive: object, payloads: dict[str, object]) -> None:
    """Write synthetic RIDB JSON members into a zip archive."""
    import json
    import zipfile
    from pathlib import Path

    assert isinstance(archive, Path)
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in payloads.items():
            zf.writestr(name, json.dumps(data))


@pytest.mark.anyio
async def test_recreation_gov_ridb_zip_populates_discovery_capabilities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: datetime.date | object
) -> None:
    """Stream RIDB campsite, attribute, and permitted-equipment files into Campground & Search."""
    from pathlib import Path

    from sqlalchemy import select

    from camply.db.models import Campground, Search

    assert isinstance(tmp_path, Path)
    engine, maker = await _setup_atomic_catalog_db(monkeypatch)
    archive = tmp_path / "ridb.zip"
    payloads: dict[str, object] = {
        "RecAreas_API_v1.json": {
            "RECDATA": [
                {
                    "RecAreaID": "area-1",
                    "OrgRecAreaID": None,
                    "ParentOrgID": None,
                    "RecAreaName": "Synthetic Alpine Park",
                    "RecAreaDescription": "Park",
                    "RecAreaLongitude": -119.5,
                    "RecAreaLatitude": 37.7,
                    "Reservable": True,
                    "Enabled": True,
                    "LastUpdatedDate": "2027-07-01",
                }
            ]
        },
        "RecAreaAddresses_API_v1.json": {"RECDATA": []},
        "Facilities_API_v1.json": {
            "RECDATA": [
                {
                    "FacilityID": "cg-water-only",
                    "ParentRecAreaID": "area-1",
                    "FacilityName": "Water Only Tent CG",
                    "FacilityDescription": "Tent sites with water",
                    "FacilityTypeDescription": "Campground",
                    "FacilityLongitude": -119.5,
                    "FacilityLatitude": 37.7,
                    "Reservable": True,
                    "Enabled": True,
                },
                {
                    "FacilityID": "cg-full",
                    "ParentRecAreaID": "area-1",
                    "FacilityName": "Full Hookup RV CG",
                    "FacilityDescription": "RV sites",
                    "FacilityTypeDescription": "Campground",
                    "FacilityLongitude": -119.4,
                    "FacilityLatitude": 37.8,
                    "Reservable": True,
                    "Enabled": True,
                },
            ]
        },
        "FacilityAddresses_API_v1.json": {"RECDATA": []},
        "Campsites_API_v1.json": {
            "RECDATA": [
                {
                    "CampsiteID": 1001,
                    "FacilityID": "cg-water-only",
                    "CampsiteName": "T01",
                    "CampsiteType": "TENT ONLY NONELECTRIC",
                    "TypeOfUse": "Overnight",
                    "CampsiteAccessible": False,
                },
                {
                    "CampsiteID": 1002,
                    "FacilityID": "cg-water-only",
                    "CampsiteName": "DAY01",
                    "CampsiteType": "DAY USE PICNIC",
                    "TypeOfUse": "Day",
                    "CampsiteAccessible": True,
                },
                {
                    "CampsiteID": 2001,
                    "FacilityID": "cg-full",
                    "CampsiteName": "RV01",
                    "CampsiteType": "RV ELECTRIC",
                    "TypeOfUse": "Overnight",
                    "CampsiteAccessible": True,
                },
            ]
        },
        "CampsiteAttributes_API_v1.json": {
            "RECDATA": [
                {
                    "EntityID": 1001,
                    "AttributeName": "Water Hookup",
                    "AttributeValue": "Yes",
                },
                {
                    "EntityID": 1001,
                    "AttributeName": "Sewer Hookup",
                    "AttributeValue": "Yes",
                },
                {
                    "EntityID": 1001,
                    "AttributeName": "Electricity Hookup",
                    "AttributeValue": "No",
                },
                {
                    "EntityID": 1001,
                    "AttributeName": "Pets Allowed",
                    "AttributeValue": "Domestic",
                },
                {
                    "EntityID": 2001,
                    "AttributeName": "Water Hookup",
                    "AttributeValue": "Yes",
                },
                {
                    "EntityID": 2001,
                    "AttributeName": "Electricity Hookup",
                    "AttributeValue": "50 Amp",
                },
            ]
        },
        "PermittedEquipment_API_v1.json": {
            "RECDATA": [
                {"CampsiteID": 1001, "EquipmentName": "Tent", "MaxLength": 14.0},
                {"CampsiteID": 2001, "EquipmentName": "RV", "MaxLength": 38.9},
                {"CampsiteID": 2001, "EquipmentName": "Trailer", "MaxLength": 32.0},
                {"CampsiteID": 2001, "EquipmentName": "Tent", "MaxLength": 12.0},
            ]
        },
    }
    _write_ridb_zip(archive, payloads)

    provider = RecreationGovProvider()
    monkeypatch.setattr(
        provider, "download_offline_data", AsyncMock(return_value=archive)
    )
    try:
        await provider.populate_database()
        async with maker() as session:
            water_only = await session.get(Campground, ("cg-water-only", 1))
            full = await session.get(Campground, ("cg-full", 1))
            assert water_only is not None
            assert (
                water_only.has_water,
                water_only.has_sewer,
                water_only.has_electric,
                water_only.pets_allowed,
                water_only.ada_accessible,
                water_only.max_rv_length,
                water_only.campsite_types,
            ) == (True, True, False, True, False, None, ["TENT"])
            assert full is not None
            assert (
                full.has_electric,
                full.has_water,
                full.has_sewer,
                full.ada_accessible,
                full.max_rv_length,
                sorted(full.campsite_types or []),
            ) == (True, True, False, True, 38, ["RV", "TENT"])

            area_search = (
                await session.scalars(
                    select(Search).where(
                        Search.provider_id == 1,
                        Search.entity_type == "RecreationArea",
                        Search.recreation_area_id == "area-1",
                    )
                )
            ).one()
            assert (
                area_search.has_electric,
                area_search.has_water,
                area_search.has_sewer,
                area_search.pets_allowed,
                area_search.ada_accessible,
                area_search.max_rv_length,
                sorted(area_search.campsite_types or []),
            ) == (True, True, True, True, True, 38, ["RV", "TENT"])

        # Re-sync with cg-full losing overnight sites clears stale capabilities
        campsites_data = payloads["Campsites_API_v1.json"]
        assert isinstance(campsites_data, dict)
        campsites_data["RECDATA"] = campsites_data["RECDATA"][:2]
        _write_ridb_zip(archive, payloads)
        await provider.populate_database()
        async with maker() as session:
            cleared_full = await session.get(Campground, ("cg-full", 1))
            assert cleared_full is not None
            assert (
                cleared_full.has_electric,
                cleared_full.has_water,
                cleared_full.ada_accessible,
                cleared_full.max_rv_length,
                cleared_full.campsite_types,
            ) == (False, False, False, None, None)
    finally:
        await provider.async_client.aclose()
        await engine.dispose()


def test_recreation_gov_site_dto_extracts_equipment_and_vehicle_length() -> None:
    """Recreation.gov site DTO normalizes permitted_equipment and floors RV/trailer length only."""
    from types import SimpleNamespace

    from camply.providers.recreation_gov.models.api import (
        RecDotGovAttribute,
        RecDotGovCampsite,
        RecDotGovEquipment,
    )

    provider = RecreationGovProvider()
    rv_meta = RecDotGovCampsite(
        campsite_id=101,
        name="Site 101",
        type="RV ELECTRIC",
        accessible=True,
        permitted_equipment=[
            RecDotGovEquipment(equipment_name="RV", max_length=34.7),
            RecDotGovEquipment(equipment_name="Trailer", max_length=28.0),
            RecDotGovEquipment(equipment_name="Tent", max_length=20.0),
        ],
    )
    site_stub = SimpleNamespace(
        site="Site 101",
        campsite_type="RV ELECTRIC",
        max_num_people=6,
        loop="Loop A",
        type_of_use="Overnight",
    )
    dto = provider._create_campsite_dto(
        campsite_id=101,
        site_data=site_stub,
        meta_site=rv_meta,
        available_dates=[datetime.date(2030, 7, 1)],
    )
    assert dto.permitted_equipment == ["RV", "Tent", "Trailer"]
    assert dto.max_vehicle_length == 34

    tent_meta = RecDotGovCampsite(
        campsite_id=102,
        name="Site 102",
        type="TENT ONLY NONELECTRIC",
        permitted_equipment=[
            RecDotGovEquipment(equipment_name="Tent", max_length=16.0)
        ],
        attributes=[
            RecDotGovAttribute(
                attribute_id=1, attribute_name="Driveway Length", attribute_value="18"
            )
        ],
    )
    tent_dto = provider._create_campsite_dto(
        campsite_id=102,
        site_data=SimpleNamespace(
            site="Site 102",
            campsite_type="TENT ONLY NONELECTRIC",
            max_num_people=4,
            loop="Loop B",
            type_of_use="Overnight",
        ),
        meta_site=tent_meta,
        available_dates=[datetime.date(2030, 7, 1)],
    )
    assert tent_dto.permitted_equipment == ["Tent"]
    assert tent_dto.max_vehicle_length is None

    zero_meta = RecDotGovCampsite(
        campsite_id=103,
        name="Site 103",
        type="RV NONELECTRIC",
        permitted_equipment=[RecDotGovEquipment(equipment_name="RV", max_length=0.0)],
    )
    zero_dto = provider._create_campsite_dto(
        campsite_id=103,
        site_data=SimpleNamespace(
            site="Site 103",
            campsite_type="RV NONELECTRIC",
            max_num_people=6,
            loop="Loop C",
            type_of_use="Overnight",
        ),
        meta_site=zero_meta,
        available_dates=[datetime.date(2030, 7, 1)],
    )
    assert zero_dto.permitted_equipment == ["RV"]
    assert zero_dto.max_vehicle_length is None
