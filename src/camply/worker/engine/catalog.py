"""Provider catalog and independent detail refreshes shared by both runners."""

from typing import Any

import structlog

from camply.providers.base import BaseProvider
from camply.providers.enrichment import enrich_provider, stale_destinations

logger = structlog.getLogger(__name__)


async def enrich_provider_details(
    provider_id: int, provider_cls: type[BaseProvider]
) -> dict[str, Any]:
    """Refresh one due batch without importing catalogs or opening idle clients."""
    result: dict[str, Any] = {
        "provider_id": provider_id,
        "provider_name": provider_cls.__name__,
        "search_name": f"Enrich {provider_cls.__name__} Details",
        "has_more": False,
    }
    if provider_cls.enrich_metadata is BaseProvider.enrich_metadata:
        return {**result, "status": "skipped", "reason": "unsupported_provider"}
    if not await stale_destinations(provider_id, limit=1):
        return {**result, "status": "skipped", "reason": "no_due_details"}
    provider = provider_cls()
    try:
        succeeded = await enrich_provider(provider)
    finally:
        try:
            await provider.async_client.aclose()
        except Exception:
            pass
    if not succeeded:
        return {**result, "status": "error", "reason": "enrichment_failed"}
    result.update(
        status="success",
        has_more=bool(await stale_destinations(provider_id, limit=1)),
    )
    logger.info("Provider enrichment batch completed", **result)
    return result


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
        await enrich_provider(provider)
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
