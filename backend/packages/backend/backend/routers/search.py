"""
Search API — full-text and faceted search across recreation areas and campgrounds.
"""

from __future__ import annotations

import math
import time

from fastapi import APIRouter, Query

from backend.dependencies import SessionDep
from backend.metrics import SEARCH_DURATION_SECONDS, TOTAL_SEARCH_REQUESTS
from backend.schemas import SearchExploreResponse, SearchFacets, SearchResultResponse
from db.models import Search

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
    query: str = Query(default=""),
    q: str | None = Query(default=None),
    limit: int = 20,
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


@search_router.get("/search/explore")
async def search_explore(
    session: SessionDep,
    query: str = Query(default=""),
    q: str | None = Query(default=None),
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
