# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Providers
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.dependencies import SessionDep
from backend.schemas import ProviderResponse
from db.models import Provider as ProviderDB

provider_router = APIRouter(tags=["providers"])


class Provider(BaseModel):
    """
    Provider Model
    """

    id: int
    name: str
    description: str | None
    url: str
    enabled: bool


@provider_router.get("/provider/{id}")
async def get_provider(id: int, session: SessionDep) -> Provider:
    """
    Get Provider by ID
    """
    result = await session.execute(select(ProviderDB).where(ProviderDB.id == id))
    fetched = result.scalar_one_or_none()
    if fetched is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return Provider(
        id=fetched.id,
        name=fetched.name,
        description=fetched.description,
        url=fetched.url,
        enabled=fetched.enabled,
    )


@provider_router.get("/providers")
async def list_providers(session: SessionDep) -> list[ProviderResponse]:
    """
    List all supported providers.
    """
    result = await session.execute(select(ProviderDB))
    providers = result.scalars().all()
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            url=p.url,
            enabled=p.enabled,
        )
        for p in providers
    ]
