"""
Recreation.gov API and RIDB Data Models.
"""

from datetime import date, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field

from camply_core.providers.base import NullHandler


class RecDotGovEquipment(BaseModel):
    """
    Permitted equipment definition for Recreation.gov campsites.
    """

    equipment_name: str
    max_length: float


class RecDotGovAttribute(BaseModel):
    """
    Campsite attributes (e.g. electric hookup, sewer, pets allowed).
    """

    attribute_category: str | None = None
    attribute_id: int
    attribute_name: str
    attribute_value: Any


class RecDotGovCampsite(BaseModel):
    """
    Single campsite entry in Recreation.gov campsite search results.
    """

    campsite_id: int
    name: str
    type: str | None = None
    accessible: bool = False
    loop: str = ""
    latitude: float | None = None
    longitude: float | None = None
    permitted_equipment: list[RecDotGovEquipment] = Field(default_factory=list)
    attributes: list[RecDotGovAttribute] = Field(default_factory=list)


class RecDotGovCampsiteResponse(BaseModel):
    """
    Response wrapper for campsite search metadata endpoint.
    """

    campsites: list[RecDotGovCampsite]
    size: int
    start: int
    total: int


class CampsiteAvailabilityCampsite(BaseModel):
    """
    Single campsite's monthly availability block.
    """

    availabilities: dict[datetime, str] = Field(default_factory=dict)
    loop: str = "Default Loop"
    campsite_type: str | None = None
    max_num_people: int = 1
    min_num_people: int = 1
    type_of_use: str | None = None
    site: str = "Default Site"


class CampsiteAvailabilityResponse(BaseModel):
    """
    Response wrapper for monthly availability endpoint.
    """

    campsites: dict[int, CampsiteAvailabilityCampsite]


class RecreationGovCampsiteMetadata(BaseModel):
    """
    Standardized metadata block for Recreation.gov campsites.
    """

    loop: str
    site: str
    type_of_use: str | None = None
    permitted_equipment: list[RecDotGovEquipment] = Field(default_factory=list)
    attributes: list[RecDotGovAttribute] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None


class RecDotGovCampsiteSearchParams(BaseModel):
    """
    Query parameters for campsite search metadata endpoint.
    """

    start: int = 0
    size: int = 1000
    fq: list[str] = Field(default_factory=list)
    include_non_site_specific_campsites: bool = True


class RecDotGovAvailabilityParams(BaseModel):
    """
    Query parameters for campsite availability endpoint.
    """

    start_date: str


class Address(NullHandler):
    """
    Facility or Recreation Area address from RIDB.
    """

    Id: int | str = Field(validation_alias=AliasChoices("FacilityID", "RecAreaID"))
    City: str | None = None
    AddressType: str = Field(
        validation_alias=AliasChoices("FacilityAddressType", "RecAreaAddressType")
    )
    AddressStateCode: str | None = None
    PostalCode: int | str | None = None
    AddressCountryCode: str | None = None


class AddressData(BaseModel):
    """
    List wrapper for RIDB addresses.
    """

    RECDATA: list[Address] = Field(default_factory=list)

    def to_mapping(self) -> dict[int | str, Address]:
        """Convert default addresses into a mapping keyed by FacilityID/RecAreaID."""
        return {
            address.Id: address
            for address in self.RECDATA
            if address.AddressType == "Default"
        }


class RecDotGovCampground(NullHandler):
    """
    Campground facility record from RIDB.
    """

    FacilityID: int | str
    ParentRecAreaID: int | str | None = None
    FacilityName: str | None = None
    FacilityDescription: str | None = None
    FacilityTypeDescription: str
    FacilityLongitude: float = 0.0
    FacilityLatitude: float = 0.0
    Reservable: bool = False
    Enabled: bool = True


class RecDotGovCampgroundData(BaseModel):
    """
    List wrapper for RIDB campgrounds.
    """

    RECDATA: list[RecDotGovCampground] = Field(default_factory=list)
    ADDRESSES: dict[int | str, Address] = Field(default_factory=dict)


class RecDotGovRecreationArea(NullHandler):
    """
    Recreation Area record from RIDB.
    """

    RecAreaID: int | str
    OrgRecAreaID: int | str | None = None
    ParentOrgID: int | str | None = None
    RecAreaName: str | None = None
    RecAreaDescription: str | None = None
    RecAreaLongitude: float = 0.0
    RecAreaLatitude: float = 0.0
    Reservable: bool = False
    Enabled: bool = True
    LastUpdatedDate: date | None = None


class RecDotGovRecreationAreaData(BaseModel):
    """
    List wrapper for RIDB recreation areas.
    """

    RECDATA: list[RecDotGovRecreationArea] = Field(default_factory=list)
    ADDRESSES: dict[int | str, Address] = Field(default_factory=dict)
