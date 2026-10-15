"""Shared geographic predicates for map and paginated catalog discovery."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, or_, true
from sqlalchemy.sql.elements import ColumnElement

MAX_LONGITUDE = 180
"""Maximum valid geographic longitude."""


@dataclass(frozen=True)
class Bounds:
    """Geographic bounds; west greater than east crosses the antimeridian."""

    west: float
    south: float
    east: float
    north: float


def normalized_longitude(cls: Any) -> Any:
    """Canonicalize the two representations of the dateline for comparisons."""
    return case((cls.longitude == MAX_LONGITUDE, -180.0), else_=cls.longitude)


def valid_coordinates(cls: Any) -> Any:
    """Exclude missing/nonfinite/out-of-range coordinates while accepting zero."""
    return and_(cls.latitude.between(-90, 90), cls.longitude.between(-180, 180))


def viewport_filter(cls: Any, bounds: Bounds) -> Any:
    """Apply inclusive geographic bounds, including either dateline spelling."""
    lon = normalized_longitude(cls)
    longitude_filter: ColumnElement[bool]
    if bounds.west == -MAX_LONGITUDE and bounds.east == MAX_LONGITUDE:
        longitude_filter = true()
    elif bounds.west > bounds.east:
        longitude_filter = or_(lon >= bounds.west, lon <= bounds.east)
    else:
        longitude_filter = lon.between(bounds.west, bounds.east)
        if bounds.east == MAX_LONGITUDE:
            longitude_filter = or_(longitude_filter, lon == -MAX_LONGITUDE)
    return and_(cls.latitude.between(bounds.south, bounds.north), longitude_filter)
