"""
Campgrounds
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from camply.db.models import Campground as CampgroundDB
from camply.server.dependencies import SessionDep
from camply.server.models.campgrounds import Campground

campground_router = APIRouter(prefix="/campground", tags=["campgrounds"])


@campground_router.get("/{provider}/{id}")
async def get_campground(provider: int, id: str, session: SessionDep) -> Campground:
    """
    Get Campground by ID
    """
    result = await session.execute(
        select(CampgroundDB).where(
            CampgroundDB.provider_id == provider,
            CampgroundDB.id == id,
            CampgroundDB.reservable.is_(True),
        )
    )
    fetched = result.scalar_one_or_none()
    if fetched is None:
        raise HTTPException(status_code=404, detail="Campground not found")
    return Campground(
        id=fetched.id,
        provider_id=fetched.provider_id,
        recreation_area_id=fetched.recreation_area_id,
        name=fetched.name,
        description=fetched.description,
        country=fetched.country,
        state=fetched.state,
        longitude=fetched.longitude,
        latitude=fetched.latitude,
        reservable=fetched.reservable,
        enabled=fetched.enabled,
    )
