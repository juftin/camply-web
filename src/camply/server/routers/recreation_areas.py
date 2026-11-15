"""
Recreation Areas
"""

from functools import cached_property

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, computed_field
from sqlalchemy import select

from camply.db.models import Campground as CampgroundDB
from camply.db.models import RecreationArea as RecreationAreaDB
from camply.providers import PROVIDERS
from camply.providers.base import BaseProvider
from camply.providers.details import DestinationDetails
from camply.server.dependencies import SessionDep
from camply.server.models.campgrounds import Campground

recreation_area_router = APIRouter(prefix="/rec-area", tags=["recreation_areas"])


class RecreationArea(BaseModel):
    """
    Recreation Area Model
    """

    id: str
    provider_id: int
    name: str
    description: str | None
    country: str | None
    state: str | None
    longitude: float | None
    latitude: float | None
    reservable: bool = True
    enabled: bool = True
    details: DestinationDetails | None = None

    @cached_property
    def provider(self) -> type[BaseProvider]:
        """
        Get the provider instance for this recreation area.
        """
        return PROVIDERS[self.provider_id]

    @computed_field
    def url(self) -> str:
        return self.provider.get_rec_area_url(rec_area_id=self.id)


@recreation_area_router.get("/{provider}/{id}")
async def recreation_area(
    provider: int, id: str, session: SessionDep
) -> RecreationArea:
    """
    Get Recreation Area by ID
    """
    result = await session.execute(
        select(RecreationAreaDB).where(
            RecreationAreaDB.provider_id == provider,
            RecreationAreaDB.id == id,
        )
    )
    fetched = result.scalar_one_or_none()
    if fetched is None:
        raise HTTPException(status_code=404, detail="Recreation Area not found")
    return RecreationArea(
        id=fetched.id,
        provider_id=fetched.provider_id,
        name=fetched.name,
        description=fetched.description,
        details=DestinationDetails.model_validate(fetched.details)
        if fetched.details is not None
        else None,
        country=fetched.country,
        state=fetched.state,
        longitude=fetched.longitude,
        latitude=fetched.latitude,
        reservable=fetched.reservable,
        enabled=fetched.enabled,
    )


@recreation_area_router.get("/{provider}/{id}/campgrounds")
async def list_campgrounds(
    provider: int, id: str, session: SessionDep
) -> list[Campground]:
    """
    List all Campgrounds for a Recreation Area
    """
    result = await session.execute(
        select(CampgroundDB).where(
            CampgroundDB.provider_id == provider, CampgroundDB.recreation_area_id == id
        )
    )
    campgrounds = result.scalars().all()
    return [
        Campground(
            id=c.id,
            provider_id=c.provider_id,
            recreation_area_id=c.recreation_area_id,
            name=c.name,
            description=c.description,
            country=c.country,
            state=c.state,
            longitude=c.longitude,
            latitude=c.latitude,
            reservable=c.reservable,
            enabled=c.enabled,
        )
        for c in campgrounds
    ]


class MonitoringCampground(BaseModel):
    """Eligible provider-qualified choice for an area monitoring draft."""

    id: str
    provider_id: int
    recreation_area_id: str
    name: str
    state: str | None = None
    city: str | None = None


class MonitoringCampgroundsResponse(BaseModel):
    """Paged choices with independent full-area and filtered counts."""

    items: list[MonitoringCampground]
    total: int
    eligible_total: int
    limit: int
    offset: int
    has_more: bool
    catalog_revision: int


@recreation_area_router.get("/{provider}/{id}/monitoring-campgrounds")
async def monitoring_campgrounds(
    provider: int,
    id: str,
    session: SessionDep,
    query: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MonitoringCampgroundsResponse:
    """Discover complete eligible choices without changing the metadata endpoint."""
    from camply.db.coverage import eligible_members
    from camply.db.models import Provider

    area = await session.get(RecreationAreaDB, (id, provider))
    if area is None:
        raise HTTPException(status_code=404, detail="Recreation area not found")
    if not area.enabled:
        raise HTTPException(status_code=422, detail="Recreation area unavailable")
    members = await eligible_members(session, provider_id=provider, area_id=id)
    members.sort(key=lambda member: (member.name.casefold(), member.id))
    matches = [
        member
        for member in members
        if query.strip().casefold() in member.name.casefold()
    ]
    provider_row = await session.get(Provider, provider)
    return MonitoringCampgroundsResponse(
        items=[
            MonitoringCampground(
                id=cg.id,
                provider_id=cg.provider_id,
                recreation_area_id=id,
                name=cg.name,
                state=cg.state,
                city=cg.city,
            )
            for cg in matches[offset : offset + limit]
        ],
        total=len(matches),
        eligible_total=len(members),
        limit=limit,
        offset=offset,
        has_more=offset + limit < len(matches),
        catalog_revision=provider_row.catalog_revision if provider_row else 0,
    )
