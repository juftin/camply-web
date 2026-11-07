"""Validated ReserveAmerica catalog and daily site inventory models."""

import re
from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from camply.providers.dto import CampsiteDTO, CampsiteType

T = TypeVar("T")


def split_facility_id(value: str) -> tuple[str, str]:
    """Reject ambiguous IDs and prevent path/query injection in booking links."""
    if not re.fullmatch(r"[A-Z0-9]+_[0-9]+", value):
        raise ValueError("ReserveAmerica campground ID must be CONTRACT_facility")
    contract, facility = value.split("_", 1)
    return contract, facility


class Control(BaseModel):
    """Server-controlled zero-based pagination."""

    currentPage: int = Field(ge=0)
    pageSize: int = Field(gt=0)


class Page(BaseModel, Generic[T]):
    """Require pagination metadata so error envelopes cannot look like no results."""

    totalRecords: int = Field(ge=0)
    totalPages: int = Field(ge=0)
    control: Control
    records: list[T]


class Coordinates(BaseModel):
    """Optional campground map coordinates."""

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FacilityDetails(BaseModel):
    """Fields that distinguish native camping from external directory listings."""

    id: int
    contrCode: str
    stateCodes: list[str]
    verifiableAvailability: bool
    nonClientFacility: bool
    dayUseOnly: bool
    hiddenOnMap: bool = False
    facilityTypes: list[str]
    description: str | None = None
    coordinates: Coordinates | None = None

    @field_validator("contrCode")
    @classmethod
    def validate_contract(cls, value: str) -> str:
        """Keep contract IDs safe for direct API paths."""
        split_facility_id(f"{value}_0")
        return value


class Facility(BaseModel):
    """A facility is a campground; the API does not provide a parent park catalog."""

    name: str
    details: FacilityDetails

    @property
    def key(self) -> str:
        """Return the stable contract-scoped facility identity."""
        return f"{self.details.contrCode}_{self.details.id}"

    @property
    def eligible(self) -> bool:
        """Only expose verifiable native overnight camping inventory."""
        d = self.details
        return bool(
            self.name.strip()
            and d.verifiableAvailability
            and not d.nonClientFacility
            and not d.dayUseOnly
            and not d.hiddenOnMap
            and "camping" in d.facilityTypes
        )


class Attribute(BaseModel):
    """Provider attribute IDs retain meaning across translated display labels."""

    id: int
    name: str
    value: list[str] = Field(default_factory=list)


class SiteDetails(BaseModel):
    """Nightly site attributes and booking restrictions."""

    stayType: str
    siteIcon: str = ""
    callCenterReservable: bool = False
    nonSiteSpecific: bool = False
    loopName: str | None = None
    attributes: list[Attribute] = Field(default_factory=list)


class ProductInfo(BaseModel):
    """Reject day use, hourly products, tours, and unrelated businesses."""

    lineOfBusiness: str
    typeOfUse: str


class Night(BaseModel):
    """Only the exact AVAILABLE status represents bookable inventory."""

    date: date
    status: str


class Site(BaseModel):
    """A site with an explicit dated availability grid."""

    id: int
    name: str
    prodGrpName: str = ""
    prodInfo: ProductInfo
    details: SiteDetails
    reservableType: str | None = None
    availabilityGrid: list[Night]

    def to_dto(
        self, facility_id: str, nights: set[date], booking_url: str
    ) -> CampsiteDTO:
        """Translate explicit source attributes without inferring adjacent amenities."""
        attrs = {a.id: a.value for a in self.details.attributes}
        capacity = next(iter(attrs.get(12, [])), "0")
        icon = self.details.siteIcon.lower()
        kind = CampsiteType.OTHER
        if any(word in icon for word in ("cabin", "yurt", "lodge")):
            kind = CampsiteType.CABIN
        elif "rv" in icon or "trailer" in icon:
            kind = CampsiteType.RV
        elif "tent" in icon:
            kind = CampsiteType.TENT
        electric = any(
            v.strip().lower() in {"y", "yes", "true", "electric", "electricity"}
            or re.fullmatch(r"[1-9]\d*(?:\s*(?:amps?|a))?", v.strip().lower())
            is not None
            for v in attrs.get(218, [])
        )
        return CampsiteDTO(
            campsite_id=f"{facility_id}_{self.id}",
            campsite_name=self.name,
            campsite_type=kind,
            capacity=int(capacity) if capacity.isdecimal() else 0,
            available_dates=sorted(nights),
            is_electric=electric,
            is_accessible=any(
                v.lower() in {"y", "yes", "true", "1"} for v in attrs.get(104, [])
            ),
            metadata={
                "booking_url": booking_url,
                "loop": self.details.loopName,
                "site_type": self.prodGrpName,
                "attributes": [a.model_dump() for a in self.details.attributes],
                "non_site_specific": self.details.nonSiteSpecific,
            },
        )

    @property
    def eligible(self) -> bool:
        """Avoid reporting phone-only or non-overnight products."""
        return (
            self.prodInfo.lineOfBusiness == "CAMPING"
            and self.prodInfo.typeOfUse == "NIGHTLY"
            and self.details.stayType == "NIGHTLY"
            and not self.details.callCenterReservable
            and self.reservableType == "WEB_AVAILABLE"
        )


class CatalogState(BaseModel):
    """State/province coverage published in the brand catalog."""

    stateCode: str
    countryCode: str

    @field_validator("stateCode")
    @classmethod
    def validate_state(cls, value: str) -> str:
        """Validate source codes before using them in discovery requests."""
        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("Invalid ReserveAmerica state code")
        return value


class BrandCatalog(BaseModel):
    """Bulk geographical coverage; external listings still require filtering."""

    states: list[CatalogState]
