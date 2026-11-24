"""
Ingestion: Celery tasks for database population.

Data ingestion tasks that populate the database with provider data
from offline downloads (RIDB zip, recreation areas, facilities).

- ``populate_database`` orchestrator runs daily at midnight UTC via Celery
  beat, fanning out one task per registered provider. Startup ingestion is
  not currently wired to a worker signal.
- ``populate_provider_database`` is the per-provider worker with retries.
- Independent detail discovery runs every heartbeat and continues successful
  bounded batches without importing catalogs again.
"""

import asyncio

import structlog

from camply.providers import PROVIDERS
from camply.worker.celery_app import celery_app
from camply.worker.engine.catalog import (
    enrich_provider_details as _enrich_provider_details_async,
)
from camply.worker.engine.catalog import (
    populate_provider as _populate_provider_async,
)

logger = structlog.getLogger(__name__)


@celery_app.task(name="catalog.enrich_all", ignore_result=True)
def enrich_all_provider_details() -> dict:
    """Resume due detail batches independently of daily full catalog imports."""
    for provider_id in PROVIDERS:
        celery_app.send_task(
            name="catalog.enrich_provider",
            kwargs={"provider_id": provider_id},
        )
    return {
        "status": "ok",
        "provider_name": "All Providers",
        "search_name": "Discover Destination Enrichment",
        "providers_fanned_out": len(PROVIDERS),
    }


@celery_app.task(name="catalog.enrich_provider", ignore_result=True)
def enrich_provider_details(provider_id: int) -> dict:
    """Yield between bounded batches and stop immediate continuations on failure."""
    provider_cls = PROVIDERS.get(provider_id)
    if provider_cls is None:
        return {
            "status": "error",
            "provider_id": provider_id,
            "reason": "unknown_provider",
        }
    result = asyncio.run(_enrich_provider_details_async(provider_id, provider_cls))
    if result["status"] == "success" and result["has_more"]:
        celery_app.send_task(
            name="catalog.enrich_provider",
            kwargs={"provider_id": provider_id},
            countdown=1,
        )
    return result


@celery_app.task(
    name="catalog.sync_all",
    ignore_result=True,
)
def populate_database() -> dict:
    """
    Orchestrate database population for all registered providers.

    Iterates over the ``PROVIDERS`` registry and fans out a
    ``populate_provider_database`` task for each provider ID.

    Returns
    -------
    dict
        ``{"status": "ok", "providers_fanned_out": N, "provider_ids": [...]}``.
    """
    provider_ids = list(PROVIDERS.keys())
    logger.info("Fanning out ingestion tasks", provider_ids=provider_ids)

    for provider_id in provider_ids:
        celery_app.send_task(
            name="catalog.sync_provider",
            kwargs={"provider_id": provider_id},
        )

    logger.info("Ingestion fan-out complete", count=len(provider_ids))
    return {
        "status": "ok",
        "provider_name": "All Providers",
        "search_name": "Sync All Provider Catalogs",
        "providers_fanned_out": len(provider_ids),
        "provider_ids": provider_ids,
    }


@celery_app.task(
    name="catalog.sync_provider",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
    ignore_result=True,
)
def populate_provider_database(self, provider_id: int) -> dict:
    """
    Populate the database for a single provider.

    Parameters
    ----------
    provider_id : int
        The provider ID key from the ``PROVIDERS`` registry.

    Returns
    -------
    dict
        ``{"status": "success", "provider_id": N}`` on success, or
        ``{"status": "error", "provider_id": N, "reason": ...}`` on failure.
    """
    provider_cls = PROVIDERS.get(provider_id)
    if provider_cls is None:
        logger.warning("Unknown provider id", provider_id=provider_id)
        return {
            "status": "error",
            "provider_id": provider_id,
            "reason": "unknown_provider",
        }

    provider_name = provider_cls.__name__
    logger.info(
        "Starting provider ingestion",
        provider_id=provider_id,
        provider_name=provider_name,
    )

    try:
        return asyncio.run(_populate_provider_async(provider_id, provider_cls))
    except Exception as exc:
        logger.exception(
            "populate_provider_database task failed",
            provider_id=provider_id,
            provider_name=provider_name,
        )
        raise self.retry(exc=exc) from exc
