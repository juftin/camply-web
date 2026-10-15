"""Provider catalog sync reusable by local and distributed runners."""

import structlog

from providers.base import BaseProvider

logger = structlog.getLogger(__name__)


async def populate_provider(provider_id: int, provider_cls: type[BaseProvider]) -> dict:
    """
    Async implementation of per-provider database population.

    Parameters
    ----------
    provider_id : int
        The provider ID key from the ``PROVIDERS`` registry.
    provider_cls : type
        The provider class to instantiate and run.

    Returns
    -------
    dict
        ``{"status": "success", "provider_id": N}``.
    """
    provider = provider_cls()
    try:
        await provider.populate_database()
    finally:
        try:
            await provider.async_client.aclose()
        except Exception:
            pass
    logger.info(
        "Provider ingestion completed",
        provider_id=provider_id,
        provider_name=provider_cls.__name__,
    )
    return {
        "status": "success",
        "provider_id": provider_id,
        "provider_name": "Recreation.gov"
        if provider_id == 1
        else provider_cls.__name__,
        "search_name": f"Sync {provider_cls.__name__} Catalog",
    }
