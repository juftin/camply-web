"""
Tests for Recreation.gov data models — Address, Campground, RecreationArea models.
"""

import datetime

import pytest
from pydantic import ValidationError

from providers.recreation_gov.models.address import (
    Address,
    AddressData,
    AddressPopulator,
)
from providers.recreation_gov.models.campgrounds import (
    RecDotGovCampground,
    RecDotGovCampgroundData,
)
from providers.recreation_gov.models.recreation_area import (
    RecDotGovRecreationArea,
    RecDotGovRecreationAreaData,
)

# ===========================================================================
# AddressData / AddressPopulator
# ===========================================================================


class TestAddressData:
    """Tests for AddressData to_mapping."""

    def test_to_mapping(self) -> None:
        addr1 = Address(  # type: ignore[call-arg]
            FacilityID=1,
            City="Denver",
            FacilityAddressType="Default",
            AddressStateCode=None,
            PostalCode=None,
            AddressCountryCode=None,
        )
        addr2 = Address(  # type: ignore[call-arg]
            FacilityID=2,
            City="Boulder",
            FacilityAddressType="Default",
            AddressStateCode=None,
            PostalCode=None,
            AddressCountryCode=None,
        )
        addr3 = Address(  # type: ignore[call-arg]
            FacilityID=3,
            City="Ignore",
            FacilityAddressType="Mailing",  # different type
            AddressStateCode=None,
            PostalCode=None,
            AddressCountryCode=None,
        )
        data = AddressData(RECDATA=[addr1, addr2, addr3])
        mapping = data.to_mapping()
        assert 1 in mapping
        assert 2 in mapping
        assert 3 not in mapping  # filtered out by AddressType
        assert mapping[1].City == "Denver"

    def test_to_mapping_empty(self) -> None:
        data = AddressData(RECDATA=[])
        assert data.to_mapping() == {}


class TestAddressPopulator:
    """Tests for AddressPopulator base class."""

    def test_default_addresses_empty(self) -> None:
        class TestPopulator(AddressPopulator):
            async def to_database(self, session):  # type: ignore[override]
                pass

        populator = TestPopulator()
        assert populator.ADDRESSES == {}


# ===========================================================================
# RecDotGovCampground
# ===========================================================================


class TestRecDotGovCampground:
    """Tests for RecDotGovCampground model."""

    def test_minimal(self) -> None:
        cg = RecDotGovCampground(
            FacilityID="123",
            ParentRecAreaID="456",
            FacilityName=None,
            FacilityDescription=None,
            FacilityTypeDescription="Campground",
            FacilityLongitude=-105.0,
            FacilityLatitude=40.0,
            Reservable=True,
            Enabled=True,
        )
        assert cg.FacilityID == "123"
        assert cg.ParentRecAreaID == "456"
        assert cg.FacilityTypeDescription == "Campground"
        assert cg.FacilityLongitude == -105.0
        assert cg.FacilityLatitude == 40.0
        assert cg.Reservable is True
        assert cg.Enabled is True
        assert cg.FacilityName is None
        assert cg.FacilityDescription is None

    def test_full(self) -> None:
        cg = RecDotGovCampground(
            FacilityID="789",
            ParentRecAreaID="012",
            FacilityName="Test Campground",
            FacilityDescription="A nice campground",
            FacilityTypeDescription="Campground",
            FacilityLongitude=-110.0,
            FacilityLatitude=45.0,
            Reservable=True,
            Enabled=True,
        )
        assert cg.FacilityName == "Test Campground"
        assert cg.FacilityDescription == "A nice campground"

    def test_non_campground_type(self) -> None:
        cg = RecDotGovCampground(
            FacilityID="999",
            ParentRecAreaID="012",
            FacilityName="Visitor Center",
            FacilityDescription=None,
            FacilityTypeDescription="Visitor Center",
            FacilityLongitude=0.0,
            FacilityLatitude=0.0,
            Reservable=False,
            Enabled=True,
        )
        assert cg.FacilityTypeDescription == "Visitor Center"

    def test_none_parent_rec_area(self) -> None:
        cg = RecDotGovCampground(
            FacilityID="1",
            ParentRecAreaID=None,
            FacilityName=None,
            FacilityDescription=None,
            FacilityTypeDescription="Campground",
            FacilityLongitude=0.0,
            FacilityLatitude=0.0,
            Reservable=False,
            Enabled=True,
        )
        assert cg.ParentRecAreaID is None

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            RecDotGovCampground(Reservable=True, Enabled=True)  # type: ignore[call-arg]

    def test_empty_facility_name_null_handler(self) -> None:
        cg = RecDotGovCampground(
            FacilityID="2",
            ParentRecAreaID="3",
            FacilityName="",
            FacilityDescription=None,
            FacilityTypeDescription="Campground",
            FacilityLongitude=0.0,
            FacilityLatitude=0.0,
            Reservable=True,
            Enabled=True,
        )
        assert cg.FacilityName is None


class TestRecDotGovCampgroundData:
    """Basic structural tests for RecDotGovCampgroundData."""

    def test_empty_recdta(self) -> None:
        data = RecDotGovCampgroundData(RECDATA=[], ADDRESSES={})
        assert data.RECDATA == []
        assert data.ADDRESSES == {}

    def test_is_address_populator_instance(self) -> None:
        """RecDotGovCampgroundData should be a subclass of AddressPopulator."""
        assert issubclass(RecDotGovCampgroundData, AddressPopulator)


# ===========================================================================
# RecDotGovRecreationArea
# ===========================================================================


class TestRecDotGovRecreationArea:
    """Tests for RecDotGovRecreationArea model."""

    def test_minimal(self) -> None:
        ra = RecDotGovRecreationArea(
            RecAreaID="123",
            OrgRecAreaID=None,
            ParentOrgID=None,
            RecAreaName=None,
            RecAreaDescription=None,
            RecAreaLongitude=-105.0,
            RecAreaLatitude=40.0,
            Reservable=True,
            Enabled=True,
            LastUpdatedDate=datetime.date(2026, 1, 1),
        )
        assert ra.RecAreaID == "123"
        assert ra.OrgRecAreaID is None
        assert ra.ParentOrgID is None
        assert ra.RecAreaName is None
        assert ra.Reservable is True
        assert ra.Enabled is True
        assert ra.LastUpdatedDate == datetime.date(2026, 1, 1)

    def test_full(self) -> None:
        ra = RecDotGovRecreationArea(
            RecAreaID="456",
            OrgRecAreaID=789,
            ParentOrgID=1,
            RecAreaName="Test Rec Area",
            RecAreaDescription="A nice area",
            RecAreaLongitude=-110.0,
            RecAreaLatitude=45.0,
            Reservable=False,
            Enabled=True,
            LastUpdatedDate=datetime.date(2026, 6, 1),
        )
        assert ra.RecAreaName == "Test Rec Area"
        assert ra.RecAreaDescription == "A nice area"
        assert ra.Reservable is False

    def test_empty_string_converted(self) -> None:
        ra = RecDotGovRecreationArea(
            RecAreaID="789",
            OrgRecAreaID=None,
            ParentOrgID=None,
            RecAreaName="",
            RecAreaDescription="",
            RecAreaLongitude=0.0,
            RecAreaLatitude=0.0,
            Reservable=False,
            Enabled=True,
            LastUpdatedDate=datetime.date(2026, 1, 1),
        )
        assert ra.RecAreaName is None
        assert ra.RecAreaDescription is None


class TestRecDotGovRecreationAreaData:
    """Basic structural tests for RecDotGovRecreationAreaData."""

    def test_empty_recdta(self) -> None:
        data = RecDotGovRecreationAreaData(RECDATA=[], ADDRESSES={})
        assert data.RECDATA == []
        assert data.ADDRESSES == {}

    def test_is_address_populator(self) -> None:
        assert issubclass(RecDotGovRecreationAreaData, AddressPopulator)
