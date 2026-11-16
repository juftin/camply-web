"""
Providers
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from camply.db.models import Provider as ProviderDB
from camply.providers import get_provider_filter_capabilities
from camply.server.dependencies import SessionDep
from camply.server.schemas import (
    ProviderFilterCapabilitiesResponse,
    ProviderResponse,
)

provider_router = APIRouter(tags=["providers"])


def _build_provider_response(provider: ProviderDB) -> ProviderResponse:
    """Serialize a provider row along with its runtime filter capabilities."""
    caps = get_provider_filter_capabilities(provider.id)
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        description=provider.description,
        url=provider.url,
        enabled=provider.enabled,
        filter_capabilities=ProviderFilterCapabilitiesResponse(
            preferred_types=caps.preferred_types,
            require_electric=caps.require_electric,
            require_accessible=caps.require_accessible,
            min_rv_length=caps.min_rv_length,
        ),
    )


@provider_router.get("/provider/{id}")
async def get_provider(id: int, session: SessionDep) -> ProviderResponse:
    """
    Get Provider by ID
    """
    result = await session.execute(select(ProviderDB).where(ProviderDB.id == id))
    fetched = result.scalar_one_or_none()
    if fetched is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _build_provider_response(fetched)


@provider_router.get("/providers")
async def list_providers(session: SessionDep) -> list[ProviderResponse]:
    """
    List all supported providers.
    """
    result = await session.execute(select(ProviderDB))
    providers = result.scalars().all()
    return [_build_provider_response(p) for p in providers]
