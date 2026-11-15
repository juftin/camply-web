"""Portable definition identity, live membership and shared-target reconciliation."""

import datetime
import hashlib
import json

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from camply.db.models import (
    Campground,
    Provider,
    RecreationArea,
    ScanTarget,
    UniqueTarget,
    UserScan,
)

MAX_NATIVE_ID_LENGTH = 128
# Maximum persisted provider-native destination ID length.


def normalized_choices(ids: list[str]) -> list[str]:
    """Canonicalize native IDs without changing case or numeric-looking values."""
    choices = sorted({value.strip() for value in ids})
    if any(not value or len(value) > MAX_NATIVE_ID_LENGTH for value in choices):
        raise ValueError("Campground IDs must contain 1-128 characters")
    return choices


def definition_hash(
    *,
    provider_id: int,
    destination_type: str,
    destination_id: str,
    start_date: datetime.date,
    end_date: datetime.date,
    coverage_mode: str | None = None,
    selected_ids: list[str] | None = None,
) -> str:
    """Identify a saved scope independently of labels and matching preferences."""
    value = [
        1,
        provider_id,
        destination_type,
        destination_id,
        start_date.isoformat(),
        end_date.isoformat(),
        coverage_mode,
        normalized_choices(selected_ids or []),
    ]
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def scan_load_options() -> tuple:
    """Eagerly load snapshot and live catalog context for async response/matching."""
    return (
        joinedload(UserScan.target).selectinload(UniqueTarget.scan_results),
        joinedload(UserScan.target)
        .joinedload(UniqueTarget.campground)
        .joinedload(Campground.recreation_area),
        selectinload(UserScan.coverage)
        .selectinload(ScanTarget.target)
        .selectinload(UniqueTarget.scan_results),
        selectinload(UserScan.coverage)
        .selectinload(ScanTarget.target)
        .joinedload(UniqueTarget.campground)
        .joinedload(Campground.recreation_area),
    )


def live_target_condition():
    """SQL membership guard shared by discovery, scanner and administration."""
    child = exists(
        select(Campground.id)
        .join(Provider, Provider.id == Campground.provider_id)
        .where(
            Campground.id == UniqueTarget.campground_id,
            Campground.provider_id == UniqueTarget.provider_id,
            Campground.enabled.is_(True),
            Campground.reservable.is_(True),
            Provider.enabled.is_(True),
            or_(
                UserScan.destination_type == "campground",
                and_(
                    Campground.recreation_area_id == UserScan.recreation_area_id,
                    exists(
                        select(RecreationArea.id)
                        .where(
                            RecreationArea.id == Campground.recreation_area_id,
                            RecreationArea.provider_id == Campground.provider_id,
                            RecreationArea.enabled.is_(True),
                        )
                        .correlate(Campground)
                    ),
                ),
            ),
        )
        .correlate(UniqueTarget, UserScan)
    )
    return and_(UserScan.provider_id == UniqueTarget.provider_id, child)


def subscriber_condition():
    """Accept legacy campground pointers and resolved area links with live guards."""
    return and_(
        or_(
            UserScan.target_id == UniqueTarget.id,
            exists(
                select(ScanTarget.scan_id)
                .where(
                    ScanTarget.scan_id == UserScan.id,
                    ScanTarget.target_id == UniqueTarget.id,
                    ScanTarget.coverage_revision == UserScan.coverage_revision,
                )
                .correlate(UserScan, UniqueTarget)
            ),
        ),
        live_target_condition(),
    )


def live_targets(scan: UserScan) -> list[UniqueTarget]:
    """Intersect resolved coverage with current loaded catalog membership."""
    if scan.destination_type != "recreation_area":
        return [scan.target] if scan.target is not None else []
    selected = {item["id"] for item in scan.selected_campgrounds}
    return [
        link.target
        for link in scan.coverage
        if link.coverage_revision == scan.coverage_revision
        and (cg := link.target.campground) is not None
        and cg.enabled
        and cg.reservable
        and cg.provider_id == scan.provider_id
        and cg.recreation_area_id == scan.recreation_area_id
        and cg.recreation_area is not None
        and cg.recreation_area.enabled
        and (scan.coverage_mode == "all" or cg.id in selected)
    ]


async def eligible_members(
    session: AsyncSession, *, provider_id: int, area_id: str
) -> list[Campground]:
    """Resolve the entire confirmed catalog without discovery pagination limits."""
    return list(
        await session.scalars(
            select(Campground)
            .join(Provider, Provider.id == Campground.provider_id)
            .join(
                RecreationArea,
                and_(
                    RecreationArea.id == Campground.recreation_area_id,
                    RecreationArea.provider_id == Campground.provider_id,
                ),
            )
            .where(
                Campground.provider_id == provider_id,
                Campground.recreation_area_id == area_id,
                Campground.enabled.is_(True),
                Campground.reservable.is_(True),
                RecreationArea.enabled.is_(True),
                Provider.enabled.is_(True),
            )
            .order_by(Campground.name, Campground.id)
        )
    )


async def get_or_create_target(
    session: AsyncSession,
    *,
    provider_id: int,
    campground_id: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> UniqueTarget:
    """Reuse one campground/window observation across all subscribing users."""
    value = UniqueTarget.calculate_hash(
        provider_id, campground_id, start_date, end_date
    )
    query = select(UniqueTarget).where(UniqueTarget.hash == value)
    target = await session.scalar(query)
    if target is None:
        try:
            async with session.begin_nested():
                target = UniqueTarget(
                    provider_id=provider_id,
                    campground_id=campground_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                session.add(target)
                await session.flush()
        except IntegrityError:
            target = await session.scalar(query)
            if target is None:
                raise
    return target


async def reconcile_coverage(
    session: AsyncSession, scan: UserScan, *, bump_row_version: bool = True
) -> bool:
    """Replace resolved links under a serialized provider publication/scan edit lock."""
    await session.scalar(
        select(Provider).where(Provider.id == scan.provider_id).with_for_update()
    )
    provider = await session.get(Provider, scan.provider_id)
    if provider is not None:
        guarded = await session.execute(
            update(Provider)
            .where(
                Provider.id == provider.id,
                Provider.catalog_revision == provider.catalog_revision,
            )
            .values(catalog_revision=provider.catalog_revision)
            .returning(Provider.id)
        )
        if guarded.scalar_one_or_none() is None:
            raise ValueError("Catalog changed while resolving coverage; retry")
    if scan.destination_type == "campground":
        members = [scan.campground_id] if scan.campground_id else []
    else:
        selected = {item["id"] for item in scan.selected_campgrounds}
        members = [
            cg.id
            for cg in await eligible_members(
                session,
                provider_id=scan.provider_id,
                area_id=scan.recreation_area_id or "",
            )
            if scan.coverage_mode == "all" or cg.id in selected
        ]
    targets = [
        await get_or_create_target(
            session,
            provider_id=scan.provider_id,
            campground_id=member,
            start_date=scan.start_date,
            end_date=scan.end_date,
        )
        for member in members
    ]
    desired = {target.id for target in targets}
    existing = {link.target_id for link in scan.coverage}
    if desired == existing:
        return False
    scan.coverage_revision = (scan.coverage_revision or 1) + 1
    if bump_row_version:
        scan.row_version = (scan.row_version or 1) + 1
    scan.last_full_checked_at = None
    scan.current_round_id = None
    scan.round_completed_at = None
    for link in list(scan.coverage):
        if link.target_id not in desired:
            scan.coverage.remove(link)
        else:
            link.coverage_revision = scan.coverage_revision
            link.round_id = None
            link.attempt_id = None
            link.outcome = "pending"
    for target in targets:
        if target.id not in existing:
            scan.coverage.append(
                ScanTarget(
                    target=target,
                    coverage_revision=scan.coverage_revision,
                    outcome="pending",
                )
            )
    await session.flush()
    return True
