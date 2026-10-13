"""Park and campground metadata exposed by UseDirect."""

from pydantic import BaseModel


class Place(BaseModel):
    """A provider park mapped to a recreation area."""

    PlaceId: int
    Name: str | None
    Description: str | None = None
    City: str | None = None
    State: str | None = None
    Latitude: float | None = None
    Longitude: float | None = None
    AllowWebBooking: bool | None = None
    IsWebViewable: bool | None = None


class Facility(BaseModel):
    """A park's campground whose upstream ID is the scan target."""

    FacilityId: int
    PlaceId: int
    Name: str | None
    Description: str | None = None
    AllowWebBooking: bool | None = None
