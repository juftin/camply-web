"""Bounded provider metadata refreshes independent of request and scan paths."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast

import structlog
from sqlalchemy import or_, select, update

from camply.db.config import db
from camply.db.models import Campground, RecreationArea
from camply.providers.details import DestinationDetails

logger = structlog.getLogger(__name__)

if TYPE_CHECKING:
    from camply.providers.base import BaseProvider

FRESHNESS = timedelta(days=7)
"""Successful enrichment remains fresh independently of catalog update times."""
MAX_BATCH = 100
"""Maximum stale destinations processed per provider refresh."""


@dataclass(frozen=True)
class Destination:
    """Provider-scoped identity supplied to a destination-specific fetcher."""

    entity_type: str
    id: str
    name: str
    recreation_area_id: str | None = None


async def stale_destinations(
    provider_id: int, *, limit: int = 100
) -> list[Destination]:
    """Select the oldest stale enabled records, bounded across both entity types."""
    if not 1 <= limit <= MAX_BATCH:
        raise ValueError("Enrichment batch size must be between 1 and 100")
    now = datetime.now(timezone.utc)
    cutoff = (now - FRESHNESS).isoformat()
    retry_cutoff = now - timedelta(hours=1)
    candidates: list[tuple[str, str, Destination]] = []
    async with db.get_session() as session:
        for model, kind in (
            (Campground, "campground"),
            (RecreationArea, "recreation_area"),
        ):
            timestamp = model.details["fetched_at"].as_string()
            query = (
                select(model)
                .where(
                    model.provider_id == provider_id,
                    model.enabled.is_(True),
                    or_(timestamp.is_(None), timestamp < cutoff),
                    or_(
                        model.details_attempted_at.is_(None),
                        model.details_attempted_at < retry_cutoff,
                    ),
                )
                .order_by(
                    model.details_attempted_at.asc().nulls_first(),
                    timestamp.asc().nulls_first(),
                    model.id,
                )
                .limit(limit)
            )
            if model is Campground:
                query = query.where(Campground.reservable.is_(True))
            for record in (await session.scalars(query)).all():
                row = cast(Campground | RecreationArea, record)
                previous = row.details or {}
                candidates.append(
                    (
                        row.details_attempted_at.isoformat()
                        if row.details_attempted_at
                        else "",
                        str(previous.get("fetched_at", "")),
                        Destination(
                            entity_type=kind,
                            id=row.id,
                            name=row.name,
                            recreation_area_id=row.recreation_area_id
                            if isinstance(row, Campground)
                            else None,
                        ),
                    )
                )
    candidates.sort(
        key=lambda item: (item[0], item[1], item[2].entity_type, item[2].id)
    )
    return [destination for _, _, destination in candidates[:limit]]


async def save_details(
    provider_id: int, destination: Destination, details: DestinationDetails
) -> None:
    """Replace a complete snapshot using its provider-qualified entity identity."""
    model = Campground if destination.entity_type == "campground" else RecreationArea
    async with db.get_session() as session:
        async with session.begin():
            await session.execute(
                update(model)
                .where(model.provider_id == provider_id, model.id == destination.id)
                .values(details=details.model_dump(mode="json"))
            )


async def mark_attempt(provider_id: int, destination: Destination) -> bool:
    """Claim a due attempt atomically so concurrent refreshes do not duplicate work."""
    model = Campground if destination.entity_type == "campground" else RecreationArea
    now = datetime.now(timezone.utc)
    async with db.get_session() as session:
        async with session.begin():
            result = await session.execute(
                update(model)
                .where(
                    model.provider_id == provider_id,
                    model.id == destination.id,
                    or_(
                        model.details_attempted_at.is_(None),
                        model.details_attempted_at < now - timedelta(hours=1),
                    ),
                )
                .values(details_attempted_at=now)
                .returning(model.id)
            )
            return result.scalar_one_or_none() is not None


async def refresh_destinations(
    provider_id: int,
    fetch: Callable[[Destination], Awaitable[DestinationDetails | None]],
    *,
    limit: int = 100,
) -> None:
    """Refresh a stale batch, preserving each last-good snapshot on source failure."""
    for destination in await stale_destinations(provider_id, limit=limit):
        try:
            if not await mark_attempt(provider_id, destination):
                continue
            details = await fetch(destination)
            if details is not None:
                await save_details(provider_id, destination, details)
        except Exception as exc:
            logger.warning(
                "Destination enrichment failed; cached details retained",
                provider_id=provider_id,
                entity_type=destination.entity_type,
                entity_id=destination.id,
                error_type=type(exc).__name__,
            )


async def enrich_provider(provider: "BaseProvider") -> None:
    """Run a provider extension without downgrading a successful catalog import."""
    try:
        await provider.enrich_metadata()
    except Exception as exc:
        logger.warning(
            "Provider enrichment failed; catalog retained",
            provider_type=type(provider).__name__,
            error_type=type(exc).__name__,
        )
