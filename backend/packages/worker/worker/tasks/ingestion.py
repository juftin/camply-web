"""
Ingestion: populate_database Celery task.

Data ingestion task that populates the database with provider data
from offline downloads (RIDB zip, recreation areas, facilities).
Runs on worker startup and daily at midnight via Celery beat.
"""

import asyncio

import structlog

from providers.recreation_gov.provider import RecreationGovProvider
from worker.celery_app import celery_app

logger = structlog.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.ingestion.populate_database",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes between retries for a heavy task
    acks_late=True,
)
def populate_database(self) -> dict:
    """
    Populate the database with provider data from offline sources.

    Downloads the RIDB zip from Recreation.gov, processes recreation areas
    and facilities, populates database tables, and rebuilds the search index.
    This is the Celery-wrapped equivalent of the ``populate-database`` CLI.

    Returns:
        dict with status key: ``{"status": "success"}`` or
        ``{"status": "error", "reason": ...}``.
    """
    try:
        return asyncio.run(_populate_database_async())
    except Exception:
        logger.exception("populate_database task failed")
        try:
            raise self.retry(exc=Exception("populate_database failed"))
        except Exception:
            return {"status": "error", "reason": "unhandled_exception"}


async def _populate_database_async() -> dict:
    """
    Async implementation of database population.
    """
    logger.info("Starting database population from offline data")
    provider = RecreationGovProvider()
    try:
        await provider.populate_database()
    finally:
        try:
            await provider.async_client.aclose()
        except Exception:
            pass
    logger.info("Database population completed successfully")
    return {"status": "success"}
