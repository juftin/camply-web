"""
Search API — full-text and faceted search across recreation areas and campgrounds.
"""

from __future__ import annotations

import math
import time
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import SessionDep
from backend.metrics import SEARCH_DURATION_SECONDS, TOTAL_SEARCH_REQUESTS
from backend.schemas import (
    GeographicBounds,
    SearchExploreResponse,
    SearchFacets,
    SearchMapGroup,
    SearchMapLocation,
    SearchMapMembersResponse,
    SearchMapResponse,
    SearchMapSummaryResponse,
    SearchResultResponse,
)
from db.models import Search
from db.search_maps import Bounds, map_features, map_members, map_summary, parse_cell

search_router = APIRouter(tags=["search"])


def _row_to_result(row: Search) -> SearchResultResponse:
    """Map Search ORM row to SearchResultResponse schema."""
    return SearchResultResponse(
        id=row.id,
        entity_type=row.entity_type,
        provider_id=row.provider_id,
        provider_name=row.provider_name,
        recreation_area_id=row.recreation_area_id,
        recreation_area_name=row.recreation_area_name,
        campground_id=row.campground_id,
        campground_name=row.campground_name,
        city=row.city,
        state=row.state,
        country=row.country,
        latitude=row.latitude,
        longitude=row.longitude,
        reservable=row.reservable,
        campsite_types=row.campsite_types or [],
        has_electric=row.has_electric,
        has_water=row.has_water,
        has_sewer=row.has_sewer,
        pets_allowed=row.pets_allowed,
        ada_accessible=row.ada_accessible,
        max_rv_length=row.max_rv_length,
    )


@search_router.get("/search")
async def search(
    session: SessionDep,
    query: str = Query(default="", max_length=200),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    provider_id: int | None = None,
    entity_type: str | None = None,
    state: str | None = None,
    has_electric: bool | None = None,
    pets_allowed: bool | None = None,
    min_rv_length: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float | None = None,
) -> list[SearchResultResponse]:
    """
    Database Search for Recreation Areas and Campgrounds (flat list format).
    """
    search_term = q if q is not None else query
    # If no query and no filters, return empty list for fast return
    if (
        not search_term.strip()
        and provider_id is None
        and not entity_type
        and not state
        and has_electric is None
        and pets_allowed is None
        and min_rv_length is None
        and lat is None
    ):
        return []

    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()

    provider_ids = [provider_id] if provider_id is not None else None
    entity_types = [entity_type] if entity_type else None

    search_rows = await Search.algorithm(
        session=session,
        term=search_term,
        limit=limit,
        provider_ids=provider_ids,
        entity_types=entity_types,
        state=state,
        has_electric=has_electric,
        pets_allowed=pets_allowed,
        min_rv_length=min_rv_length,
        lat=lat,
        lng=lng,
        radius_miles=radius_miles,
    )
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)

    return [_row_to_result(row) for row in search_rows]


def _explore_bounds(
    west: float | None = Query(default=None, ge=-180, le=180, allow_inf_nan=False),
    south: float | None = Query(default=None, ge=-90, le=90, allow_inf_nan=False),
    east: float | None = Query(default=None, ge=-180, le=180, allow_inf_nan=False),
    north: float | None = Query(default=None, ge=-90, le=90, allow_inf_nan=False),
) -> Bounds | None:
    """Allow unbounded discovery or a complete, validated map viewport."""
    if all(value is None for value in (west, south, east, north)):
        return None
    if west is None or south is None or east is None or north is None:
        raise HTTPException(
            status_code=422, detail="All four viewport bounds are required"
        )
    return _map_bounds(west=west, south=south, east=east, north=north)


@search_router.get("/search/explore")
async def search_explore(
    session: SessionDep,
    bounds: Annotated[Bounds | None, Depends(_explore_bounds)],
    query: str = Query(default="", max_length=200),
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="relevance"),
    provider_id: int | None = None,
    entity_type: str | None = None,
    state: str | None = None,
    has_electric: bool | None = None,
    pets_allowed: bool | None = None,
    min_rv_length: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float | None = None,
) -> SearchExploreResponse:
    """
    Faceted, paginated exploration endpoint for the dedicated discovery UI.
    """
    search_term = q if q is not None else query
    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()

    offset = (page - 1) * page_size
    provider_ids = [provider_id] if provider_id is not None else None
    entity_types = [entity_type] if entity_type else None

    search_rows, total, facets = await Search.search(
        session=session,
        term=search_term,
        provider_ids=provider_ids,
        entity_types=entity_types,
        state=state,
        has_electric=has_electric,
        pets_allowed=pets_allowed,
        min_rv_length=min_rv_length,
        lat=lat,
        lng=lng,
        radius_miles=radius_miles,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        bounds=bounds,
    )
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)

    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return SearchExploreResponse(
        items=[_row_to_result(row) for row in search_rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        facets=SearchFacets(
            providers=facets.get("providers", {}),
            states=facets.get("states", {}),
            entity_types=facets.get("entity_types", {}),
        ),
    )


def _map_filters(
    query: str = Query(default="", max_length=200),
    q: str | None = Query(default=None, max_length=200),
    provider_id: int | None = None,
    entity_type: str | None = None,
    state: str | None = None,
    has_electric: bool | None = None,
    pets_allowed: bool | None = None,
    min_rv_length: int | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: float | None = None,
) -> dict[str, Any]:
    """Preserve list-search input semantics for every public map endpoint."""
    return {
        "term": q if q is not None else query,
        "provider_ids": [provider_id] if provider_id is not None else None,
        "entity_types": [entity_type] if entity_type else None,
        "state": state,
        "has_electric": has_electric,
        "pets_allowed": pets_allowed,
        "min_rv_length": min_rv_length,
        "lat": lat,
        "lng": lng,
        "radius_miles": radius_miles,
    }


def _map_bounds(
    west: float = Query(ge=-180, le=180, allow_inf_nan=False),
    south: float = Query(ge=-90, le=90, allow_inf_nan=False),
    east: float = Query(ge=-180, le=180, allow_inf_nan=False),
    north: float = Query(ge=-90, le=90, allow_inf_nan=False),
) -> Bounds:
    """Validate request extents separately from possibly degenerate summaries."""
    if south >= north or west == east or (west, east) == (180, -180):
        raise HTTPException(
            status_code=422, detail="Map viewport must have positive height and width"
        )
    return Bounds(west=west, south=south, east=east, north=north)


MapFiltersDep = Annotated[dict[str, Any], Depends(_map_filters)]
"""Existing membership inputs with no list pagination or sorting."""
MapBoundsDep = Annotated[Bounds, Depends(_map_bounds)]
"""Validated map-only viewport input."""


@search_router.get("/search/map/summary")
async def search_map_summary(
    session: SessionDep, filters: MapFiltersDep
) -> SearchMapSummaryResponse:
    """Get global filtered counts and initial circular map bounds."""
    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()
    result = await map_summary(session, filters=filters)
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)
    return SearchMapSummaryResponse(**asdict(result))


@search_router.get("/search/map")
async def search_map(
    session: SessionDep,
    filters: MapFiltersDep,
    bounds: MapBoundsDep,
    zoom: int = Query(ge=0, le=19),
) -> SearchMapResponse:
    """Represent all matching visible places in bounded geographic groups."""
    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()
    result = await map_features(session, bounds=bounds, zoom=zoom, filters=filters)
    features: list[SearchMapLocation | SearchMapGroup] = []
    for cell in result.cells:
        if cell.item is not None:
            features.append(
                SearchMapLocation(cell_id=cell.cell_id, item=_row_to_result(cell.item))
            )
        else:
            features.append(
                SearchMapGroup(
                    cell_id=cell.cell_id,
                    count=cell.count,
                    latitude=cell.latitude,
                    longitude=cell.longitude,
                    bounds=GeographicBounds(**asdict(cell.bounds)),
                )
            )
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)
    return SearchMapResponse(
        viewport=GeographicBounds(**asdict(bounds)),
        grid_level=result.grid_level,
        represented_total=sum(cell.count for cell in result.cells),
        features=features,
    )


@search_router.get("/search/map/members")
async def search_map_members(
    session: SessionDep,
    filters: MapFiltersDep,
    bounds: MapBoundsDep,
    cell_id: str = Query(max_length=32),
    after_id: str | None = Query(default=None, max_length=128),
    page_size: int = Query(default=50, ge=1, le=100),
) -> SearchMapMembersResponse:
    """Page through a selected group's members, even at identical coordinates."""
    try:
        parse_cell(cell_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()
    result = await map_members(
        session,
        bounds=bounds,
        cell_id=cell_id,
        filters=filters,
        after_id=after_id,
        page_size=page_size,
    )
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)
    return SearchMapMembersResponse(
        items=[_row_to_result(item) for item in result.items],
        total=result.total,
        next_cursor=result.next_cursor,
    )
