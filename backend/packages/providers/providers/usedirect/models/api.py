"""Parse UseDirect inventory and translate it to worker DTOs.

Attributes
----------
_OVERNIGHT_USE_TYPE : int
    RDR use type for nightly inventory, excluding day use and timed rentals.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from providers.dto import CampsiteDTO, CampsiteType

_OVERNIGHT_USE_TYPE = 4


class UnitTypeGroup(BaseModel):
    """Name a provider-specific campsite classification."""

    UnitTypesGroupId: int
    UnitTypesGroupName: str


class SleepingUnit(BaseModel):
    """Name a supported equipment type without relying on fixed numeric IDs."""

    SleepingUnitId: int
    SleepingUnitName: str


class SearchFilters(BaseModel):
    """Look up inventory classification and equipment from the filters endpoint."""

    UnitTypesGroups: list[UnitTypeGroup] = Field(default_factory=list)
    NightlySleepingUnits: list[SleepingUnit] = Field(default_factory=list)


class AvailabilitySlice(BaseModel):
    """One night of inventory; a free slice may still be unbookable online."""

    Date: date
    IsFree: bool
    IsBlocked: bool | None = False
    IsWalkin: bool | None = False
    IsReservationDraw: bool | None = False
    Lock: Any = None
    MinStay: int | None = None

    @property
    def bookable(self) -> bool:
        """Exclude blocks, walk-in inventory, draws, and active reservation locks."""
        return self.IsFree and not any(
            (
                self.IsBlocked,
                self.IsWalkin,
                self.IsReservationDraw,
                self.Lock is not None,
            )
        )


class AvailabilityUnit(BaseModel):
    """A real campsite identified by UnitId, independent of the grid key."""

    UnitId: int | None = None
    Name: str | None = None
    ShortName: str | None = None
    AllowWebBooking: bool | None = None
    IsWebViewable: bool | None = None
    IsFiltered: bool | None = False
    IsAda: bool | None = False
    UseType: int | None = None
    UnitCategoryId: int | None = None
    UnitTypeGroupId: int | None = None
    SleepingUnitIds: list[int] | None = None
    VehicleLength: int | None = None
    MaxPersonOccupancy: int | None = None
    Slices: dict[str, AvailabilitySlice] | None = None

    def to_dto(
        self, *, filters: SearchFilters, start_date: date, end_date: date
    ) -> CampsiteDTO | None:
        """Translate online overnight inventory within a half-open date interval.

        Unknown capacity is represented by zero. Electrical hookups require
        an explicit electrical classification; water/sewer hookups alone
        do not establish electricity. Minimum stays remain in metadata for
        the worker's future provider-aware stay filtering.
        """
        if (
            self.UnitId is None
            or self.AllowWebBooking is not True
            or self.IsWebViewable is False
            or self.IsFiltered
            or self.UseType != _OVERNIGHT_USE_TYPE
        ):
            return None
        slices = [
            s
            for s in (self.Slices or {}).values()
            if start_date <= s.Date < end_date and s.bookable
        ]
        if not slices:
            return None
        group = next(
            (
                g.UnitTypesGroupName
                for g in filters.UnitTypesGroups
                if g.UnitTypesGroupId == self.UnitTypeGroupId
            ),
            "",
        )
        equipment = sorted(
            {
                s.SleepingUnitName
                for s in filters.NightlySleepingUnits
                if s.SleepingUnitId in (self.SleepingUnitIds or [])
            }
        )
        group_lower = group.lower()
        compact_group = group_lower.replace("-", "").replace(" ", "")
        if any(word in group_lower for word in ("cabin", "cottage", "yurt", "lodging")):
            campsite_type = CampsiteType.CABIN
        elif "tent" in group_lower and "rv" not in group_lower:
            campsite_type = CampsiteType.TENT
        elif "rv" in group_lower or any(
            word in name.lower()
            for name in equipment
            for word in ("rv", "trailer", "motorhome")
        ):
            campsite_type = CampsiteType.RV
        elif any("tent" in name.lower() for name in equipment):
            campsite_type = CampsiteType.TENT
        else:
            campsite_type = CampsiteType.OTHER
        return CampsiteDTO(
            campsite_id=str(self.UnitId),
            campsite_name=self.Name or self.ShortName or str(self.UnitId),
            campsite_type=campsite_type,
            capacity=self.MaxPersonOccupancy or 0,
            available_dates=sorted({s.Date for s in slices}),
            is_electric=("electric" in group_lower or "(e" in compact_group)
            and not any(
                word in compact_group
                for word in (
                    "nonelectric",
                    "noelectric",
                    "unelectrified",
                    "unpowered",
                    "nohookups",
                )
            ),
            is_accessible=self.IsAda is True,
            metadata={
                "unit_category_id": self.UnitCategoryId,
                "unit_type_group_id": self.UnitTypeGroupId,
                "unit_type_group": group,
                "sleeping_unit_ids": self.SleepingUnitIds or [],
                "permitted_equipment": equipment,
                "vehicle_length": self.VehicleLength,
                "minimum_stays": {
                    s.Date.isoformat(): s.MinStay
                    for s in slices
                    if s.MinStay is not None
                },
            },
        )


class AvailabilityFacility(BaseModel):
    """Inventory for one facility, including season and lottery flags."""

    FacilityId: int
    FacilityAllowWebBooking: bool | None = None
    IsReservationDraw: bool | None = False
    SeasonDates: dict[datetime, bool] | None = None
    Units: dict[str, AvailabilityUnit] | None = None

    def to_dtos(
        self, *, filters: SearchFilters, start_date: date, end_date: date
    ) -> list[CampsiteDTO]:
        """Apply facility booking and season restrictions to each unit's DTO."""
        if self.IsReservationDraw or self.FacilityAllowWebBooking is False:
            return []
        closed_dates = {
            d.date()
            for d, in_season in (self.SeasonDates or {}).items()
            if not in_season
        }
        results: list[CampsiteDTO] = []
        for unit in (self.Units or {}).values():
            dto = unit.to_dto(filters=filters, start_date=start_date, end_date=end_date)
            if dto is None:
                continue
            dto.available_dates = [
                d for d in dto.available_dates if d not in closed_dates
            ]
            if dto.available_dates:
                results.append(dto)
        return results


class AvailabilityResponse(BaseModel):
    """An empty facility is a successful response with no inventory."""

    Facility: AvailabilityFacility | None
    Message: str = ""
    NightsActual: int | None = None
