"""Bounded geographic discovery over the existing Search catalog predicates."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from camply.db.models import Search
from camply.db.models.search import build_search_filters
from camply.db.search_bounds import (
    Bounds,
    normalized_longitude,
    valid_coordinates,
    viewport_filter,
)

MAX_LATITUDE = 90
"""Maximum valid geographic latitude."""
MAX_LONGITUDE = 180
"""Maximum valid geographic longitude."""
MAX_GRID_LEVEL = 20
"""Maximum geographic grid resolution."""
MAX_MEMBER_PAGE = 100
"""Maximum number of places in a member page."""
MAX_SEARCH_ID_LENGTH = 128
"""Storage limit for the qualified Search primary key."""
CELL_PARTS = 3
"""Number of integer components in a public cell identifier."""
MAX_CELL_DIGITS = 7
"""Decimal width needed for grid coordinates through level twenty."""

MAX_MAP_FEATURES = 512
"""Maximum cells transferred for a viewport, established before aggregation."""


@dataclass
class MapSummary:
    """Global filtered counts and a minimal circular longitude extent."""

    total: int
    mappable_total: int
    unmappable_total: int
    bounds: Bounds | None


@dataclass
class MapCell:
    """One bounded cell with either a singleton item or grouped members."""

    cell_id: str
    count: int
    latitude: float
    longitude: float
    bounds: Bounds
    item: Search | None = None


@dataclass
class MapPage:
    """Complete representation of the filtered visible geographic area."""

    grid_level: int
    cells: list[MapCell]


@dataclass
class MemberPage:
    """A keyset page of publicly discoverable cell members."""

    items: list[Search]
    total: int
    next_cursor: str | None


async def _filters(session: AsyncSession, filters: dict[str, Any]) -> list[Any]:
    """Reuse the exact list search membership predicates without ranking."""
    return (await build_search_filters(cls=Search, session=session, **filters))[0]


def _floor(value: Any) -> Any:
    """Floor nonnegative SQL values portably despite PostgreSQL CAST rounding."""
    integer = cast(value, Integer)
    return case((integer > value, integer - 1), else_=integer)


def _grid(level: int) -> tuple[Any, Any]:
    """Assign half-open cells with explicit dateline and north-pole ownership."""
    width = 360.0 / 2**level
    return _floor((normalized_longitude(Search) + 180) / width), case(
        (Search.latitude == MAX_LATITUDE, 2 ** (level - 1) - 1),
        else_=_floor((Search.latitude + 90) / width),
    )


def _cell_capacity(bounds: Bounds, level: int) -> int:
    """Bound intersecting cells analytically, without enumerating the grid."""
    width = 360.0 / 2**level
    segments = [(bounds.west, bounds.east)]
    if bounds.west > bounds.east:
        segments = [(bounds.west, 180), (-180, bounds.east)]
    elif bounds.east == MAX_LONGITUDE and bounds.west != -MAX_LONGITUDE:
        segments.append((-180, -180))
    intervals = sorted(
        (
            min(2**level - 1, math.floor((a + 180) / width)),
            min(2**level - 1, math.floor((b + 180) / width)),
        )
        for a, b in segments
    )
    columns = 0
    previous = -1
    for start, end in intervals:
        columns += max(0, end - max(start, previous + 1) + 1)
        previous = max(previous, end)
    last_row = 2 ** (level - 1) - 1
    rows = (
        min(last_row, math.floor((bounds.north + 90) / width))
        - min(last_row, math.floor((bounds.south + 90) / width))
        + 1
    )
    return columns * rows


def parse_cell(cell_id: str) -> tuple[int, int, int]:
    """Validate public grid identifiers before constructing query predicates."""
    parts = cell_id.split(":")
    if len(parts) != CELL_PARTS or not all(
        part.isascii() and part.isdecimal() and len(part) <= MAX_CELL_DIGITS
        for part in parts
    ):
        raise ValueError("Invalid map cell identifier")
    level, x, y = map(int, parts)
    if not (
        1 <= level <= MAX_GRID_LEVEL and 0 <= x < 2**level and 0 <= y < 2 ** (level - 1)
    ):
        raise ValueError("Invalid map cell range")
    return level, x, y


async def map_summary(session: AsyncSession, *, filters: dict[str, Any]) -> MapSummary:
    """Count the full filtered catalog and find its shortest circular bounds."""
    predicates = await _filters(session, filters)
    total = int(
        (
            await session.scalar(
                select(func.count()).select_from(Search).where(*predicates)
            )
        )
        or 0
    )
    valid_filters = [*predicates, valid_coordinates(Search)]
    count, south, north = (
        await session.execute(
            select(
                func.count(), func.min(Search.latitude), func.max(Search.latitude)
            ).where(*valid_filters)
        )
    ).one()
    if not count:
        return MapSummary(
            total=total, mappable_total=0, unmappable_total=total, bounds=None
        )
    assert south is not None and north is not None
    longitudes = (
        select(normalized_longitude(Search).label("lng"))
        .where(*valid_filters)
        .distinct()
        .cte("map_longitudes")
    )
    gaps = select(
        longitudes.c.lng,
        func.lead(longitudes.c.lng).over(order_by=longitudes.c.lng).label("next_lng"),
        func.min(longitudes.c.lng).over().label("first_lng"),
    ).cte("map_gaps")
    following = func.coalesce(gaps.c.next_lng, gaps.c.first_lng + 360)
    gap_row: tuple[Any, Any] = (
        await session.execute(
            select(gaps.c.lng, following)
            .order_by((following - gaps.c.lng).desc(), gaps.c.lng)
            .limit(1)
        )
    ).one()
    east = float(gap_row[0])
    west = (float(gap_row[1]) + 180) % 360 - 180
    return MapSummary(
        total=total,
        mappable_total=int(count),
        unmappable_total=total - int(count),
        bounds=Bounds(west=west, east=east, south=float(south), north=float(north)),
    )


async def map_features(
    session: AsyncSession, *, bounds: Bounds, zoom: int, filters: dict[str, Any]
) -> MapPage:
    """Aggregate all visible matching rows into at most 512 portable SQL cells."""
    level = min(zoom + 2, 20)
    while level > 1 and _cell_capacity(bounds, level) > MAX_MAP_FEATURES:
        level -= 1
    x, y = _grid(level)
    rows = (
        await session.execute(
            select(
                x.label("x"),
                y.label("y"),
                func.count().label("n"),
                func.min(Search.id).label("first_id"),
                func.avg(Search.latitude).label("lat"),
                func.avg(normalized_longitude(Search)).label("lng"),
                func.min(Search.latitude).label("south"),
                func.max(Search.latitude).label("north"),
                func.min(normalized_longitude(Search)).label("west"),
                func.max(normalized_longitude(Search)).label("east"),
            )
            .where(
                *await _filters(session, filters),
                valid_coordinates(Search),
                viewport_filter(Search, bounds),
            )
            .group_by(x, y)
            .order_by(y, x)
        )
    ).all()
    single_ids = [row.first_id for row in rows if row.n == 1]
    items = (
        {
            item.id: item
            for item in (
                await session.scalars(select(Search).where(Search.id.in_(single_ids)))
            ).all()
        }
        if single_ids
        else {}
    )
    cells = [
        MapCell(
            cell_id=f"{level}:{row.x}:{row.y}",
            count=int(row.n),
            latitude=float(row.lat),
            longitude=float(row.lng),
            bounds=Bounds(
                west=float(row.west),
                east=float(row.east),
                south=float(row.south),
                north=float(row.north),
            ),
            item=items.get(row.first_id) if row.n == 1 else None,
        )
        for row in rows
    ]
    return MapPage(grid_level=level, cells=cells)


async def map_members(
    session: AsyncSession,
    *,
    bounds: Bounds,
    cell_id: str,
    filters: dict[str, Any],
    page_size: int = 50,
    after_id: str | None = None,
) -> MemberPage:
    """Return bounded keyset pages for the selected cell/viewport intersection."""
    level, column, row = parse_cell(cell_id)
    if not 1 <= page_size <= MAX_MEMBER_PAGE or (
        after_id is not None and len(after_id) > MAX_SEARCH_ID_LENGTH
    ):
        raise ValueError("Invalid map member pagination")
    x, y = _grid(level)
    predicates = [
        *await _filters(session, filters),
        valid_coordinates(Search),
        viewport_filter(Search, bounds),
        x == column,
        y == row,
    ]
    total = int(
        (
            await session.scalar(
                select(func.count()).select_from(Search).where(*predicates)
            )
        )
        or 0
    )
    statement = select(Search).where(*predicates)
    if after_id is not None:
        statement = statement.where(Search.id > after_id)
    items = list(
        (
            await session.scalars(statement.order_by(Search.id).limit(page_size + 1))
        ).all()
    )
    more = len(items) > page_size
    items = items[:page_size]
    return MemberPage(
        items=items, total=total, next_cursor=items[-1].id if more else None
    )
