"""
Catalog search services for recreation areas and campgrounds.
"""

from typing import Any

import httpx
import structlog

from camply_core.providers.recreation_gov.config import RecreationGovConfig
from camply_core.providers.recreation_gov.models import (
    RecDotGovCampground,
    RecDotGovRecreationArea,
)

logger = structlog.getLogger(__name__)

_DEFAULT_TIMEOUT: float = 20.0
# HTTP request timeout in seconds.

_HTTP_OK: int = 200
# Expected HTTP success status code.


async def search_recreation_areas(
    query: str | None = None,
    state: str | None = None,
    config: RecreationGovConfig | None = None,
) -> list[RecDotGovRecreationArea]:
    """
    Search for Recreation Areas on Recreation.gov matching query or state.

    Parameters
    ----------
    query : str | None
        Free-text search query for recreation area name.
    state : str | None
        Two-letter state code filter.
    config : RecreationGovConfig | None
        Configuration containing provider URLs.

    Returns
    -------
    list[RecDotGovRecreationArea]
        Matching recreation area records.
    """
    cfg = config or RecreationGovConfig()
    url = f"{cfg.base_url}api/search"
    fq_parts = ["entity_type:recarea"]
    if state:
        fq_parts.append(f"state:{state.upper()}")

    params: dict[str, Any] = {
        "fq": fq_parts,
        "size": 50,
    }
    if query:
        params["q"] = query

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; camply/0.1.0)",
        "Accept": "application/json",
    }

    results: list[RecDotGovRecreationArea] = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url=url, params=params, headers=headers, timeout=_DEFAULT_TIMEOUT
            )
            if resp.status_code == _HTTP_OK:
                data = resp.json()
                items = data.get("results", [])
                for item in items:
                    rec_id = (
                        item.get("entity_id")
                        or item.get("recarea_id")
                        or item.get("id")
                    )
                    if rec_id:
                        results.append(
                            RecDotGovRecreationArea(
                                RecAreaID=rec_id,
                                RecAreaName=item.get("name") or item.get("title"),
                                RecAreaDescription=item.get("description"),
                            )
                        )
    except Exception as exc:
        logger.warning("Recreation area search returned error", error=str(exc))

    return results


async def search_campgrounds(
    query: str | None = None,
    state: str | None = None,
    rec_area_id: int | str | None = None,
    config: RecreationGovConfig | None = None,
) -> list[RecDotGovCampground]:
    """
    Search for campgrounds matching query, state, or parent recreation area.

    Parameters
    ----------
    query : str | None
        Free-text search query for campground name.
    state : str | None
        Two-letter state code filter.
    rec_area_id : int | str | None
        ID of parent recreation area.
    config : RecreationGovConfig | None
        Configuration containing provider URLs.

    Returns
    -------
    list[RecDotGovCampground]
        Matching campground facility records.
    """
    cfg = config or RecreationGovConfig()
    url = f"{cfg.base_url}api/search"
    fq_parts = ["entity_type:campground"]
    if state:
        fq_parts.append(f"state:{state.upper()}")
    if rec_area_id:
        fq_parts.append(f"parent_asset_id:{rec_area_id}")

    params: dict[str, Any] = {
        "fq": fq_parts,
        "size": 50,
    }
    if query:
        params["q"] = query

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; camply/0.1.0)",
        "Accept": "application/json",
    }

    results: list[RecDotGovCampground] = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url=url, params=params, headers=headers, timeout=_DEFAULT_TIMEOUT
            )
            if resp.status_code == _HTTP_OK:
                data = resp.json()
                items = data.get("results", [])
                for item in items:
                    fac_id = (
                        item.get("entity_id")
                        or item.get("facility_id")
                        or item.get("id")
                    )
                    if fac_id:
                        results.append(
                            RecDotGovCampground(
                                FacilityID=fac_id,
                                FacilityName=item.get("name") or item.get("title"),
                                ParentRecAreaID=item.get("parent_id") or rec_area_id,
                                FacilityTypeDescription="Campground",
                                Reservable=bool(item.get("reservable", True)),
                            )
                        )
    except Exception as exc:
        logger.warning("Campground search returned error", error=str(exc))

    return results
