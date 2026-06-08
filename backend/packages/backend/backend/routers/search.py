"""
Search API — full-text search across recreation areas and campgrounds.
"""

import time

from fastapi import APIRouter
from pydantic import BaseModel

from backend.dependencies import SessionDep
from backend.metrics import SEARCH_DURATION_SECONDS, TOTAL_SEARCH_REQUESTS
from db.models import Search

search_router = APIRouter(tags=["search"])


class SearchResult(BaseModel):
    """
    Search Result Model
    """

    id: str
    entity_type: str
    provider_id: int
    provider_name: str
    recreation_area_id: str | None
    recreation_area_name: str | None
    campground_id: str | None
    campground_name: str | None


@search_router.get("/search")
async def search(
    query: str, session: SessionDep, limit: int = 20
) -> list[SearchResult]:
    """
    Database Search for Recreation Areas and Campgrounds
    """
    start = time.monotonic()
    TOTAL_SEARCH_REQUESTS.inc()
    search_rows = await Search.algorithm(
        session=session,
        term=query,
        limit=limit,
    )
    SEARCH_DURATION_SECONDS.observe(time.monotonic() - start)
    return [
        SearchResult(
            id=row.id,
            entity_type=row.entity_type,
            provider_id=row.provider_id,
            provider_name=row.provider_name,
            recreation_area_id=row.recreation_area_id,
            recreation_area_name=row.recreation_area_name,
            campground_id=row.campground_id,
            campground_name=row.campground_name,
        )
        for row in search_rows
    ]
