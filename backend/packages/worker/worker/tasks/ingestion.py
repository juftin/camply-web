"""
Ingestion: Celery tasks for database population.

Data ingestion tasks that populate the database with provider data
from offline downloads (RIDB zip, recreation areas, facilities).

- ``populate_database`` orchestrator runs on worker startup and daily at
  midnight via Celery beat, fanning out one task per registered provider.
- ``populate_provider_database`` is the per-provider worker with retries.
"""

import asyncio

import structlog

from providers import PROVIDERS
from worker.celery_app import celery_app

logger = structlog.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.ingestion.populate_database",
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
            name="worker.tasks.ingestion.populate_provider_database",
            kwargs={"provider_id": provider_id},
        )

    logger.info("Ingestion fan-out complete", count=len(provider_ids))
    return {
        "status": "ok",
        "providers_fanned_out": len(provider_ids),
        "provider_ids": provider_ids,
    }


@celery_app.task(
    name="worker.tasks.ingestion.populate_provider_database",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
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
        return {"status": "error", "provider_id": provider_id, "reason": "unknown_provider"}

    provider_name = provider_cls.__name__
    logger.info("Starting provider ingestion", provider_id=provider_id, provider_name=provider_name)

    try:
        return asyncio.run(_populate_provider_async(provider_id, provider_cls))
    except Exception:
        logger.exception(
            "populate_provider_database task failed",
            provider_id=provider_id,
            provider_name=provider_name,
        )
        try:
            raise self.retry(
                exc=Exception(f"populate_provider_database failed for {provider_id}")
            )
        except Exception:
            return {
                "status": "error",
                "provider_id": provider_id,
                "reason": "unhandled_exception",
            }


async def _populate_provider_async(
    provider_id: int, provider_cls: type
) -> dict:
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
    return {"status": "success", "provider_id": provider_id}
