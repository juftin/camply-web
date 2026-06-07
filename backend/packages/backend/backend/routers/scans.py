"""
Scan management router — ``/api/scans`` endpoints.

All endpoints are auth-gated through the ``CurrentUserDep`` dependency:

* **local mode** — a synthetic admin user is created on first access
  (configured via ``CAMPLY_ADMIN_EMAIL``).
* **auth0 mode** — a valid ``Authorization: Bearer <JWT>`` header is required;
  users are upserted into the database automatically.

Every endpoint also enforces an *early-access* (whitelist) gate via
the router-level ``require_early_access`` dependency — un-whitelisted
callers receive a ``403`` with error code ``ERR_EARLY_ACCESS_REQUIRED``.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.auth import CurrentUserDep, require_early_access
from backend.dependencies import SessionDep
from backend.schemas import (
    ScanCreateRequest,
    ScanDetailResponse,
    ScanListResponse,
    ScanResponse,
    ScanResultItem,
    ScanUpdateRequest,
)
from db.models import (
    Campground as CampgroundDB,
)
from db.models import (
    UniqueTarget as UniqueTargetDB,
)
from db.models import (
    UserScan as UserScanDB,
)

logger = structlog.getLogger(__name__)


scan_router = APIRouter(
    prefix="/scans",
    tags=["scans"],
    dependencies=[Depends(require_early_access)],
)


async def _lookup_campground(
    session: AsyncSession,
    provider_id: int,
    campground_id: str,
) -> CampgroundDB | None:
    """Fetch a campground row by composite key, joining its recreation area."""
    result = await session.execute(
        select(CampgroundDB)
        .options(joinedload(CampgroundDB.recreation_area))
        .where(
            CampgroundDB.provider_id == provider_id,
            CampgroundDB.id == campground_id,
            CampgroundDB.reservable.is_(True),
        )
    )
    return result.unique().scalar_one_or_none()


async def _scan_to_response(
    scan: UserScanDB,
    *,
    campground_name: str = "",
    rec_area_name: str = "",
    found_count: int = 0,
) -> ScanResponse:
    """Convert a ``UserScan`` ORM row to a ``ScanResponse``."""
    return ScanResponse(
        id=scan.id,
        provider_id=scan.target.provider_id,
        campground_id=scan.target.campground_id,
        campground_name=campground_name,
        recreation_area_name=rec_area_name,
        start_date=scan.target.start_date,
        end_date=scan.target.end_date,
        is_active=scan.is_active,
        min_stay_length=scan.min_stay_length,
        preferred_types=scan.preferred_types or [],
        require_electric=scan.require_electric,
        last_checked_at=scan.target.last_checked_at,
        found_count=found_count,
        created_at=scan.created_at,
    )


# ---------------------------------------------------------------------------
# GET  /scans
# ---------------------------------------------------------------------------


@scan_router.get("")
async def list_scans(
    current_user: CurrentUserDep,
    session: SessionDep,
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ScanListResponse:
    """List all scans belonging to the authenticated user."""

    query = (
        select(UserScanDB)
        .options(
            joinedload(UserScanDB.target).joinedload(UniqueTargetDB.scan_results),
        )
        .where(UserScanDB.user_id == current_user.id)
        .order_by(UserScanDB.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if is_active is not None:
        query = query.where(UserScanDB.is_active == is_active)

    result = await session.execute(query)
    scans = result.unique().scalars().all()

    # Batch-load all referenced campgrounds to avoid N+1 queries.
    cg_ids = {scan.target.campground_id for scan in scans}
    campground_map: dict[tuple[int, str], CampgroundDB] = {}
    if cg_ids:
        cg_result = await session.execute(
            select(CampgroundDB)
            .options(joinedload(CampgroundDB.recreation_area))
            .where(CampgroundDB.id.in_(cg_ids))
        )
        for cg_row in cg_result.unique().scalars().all():
            campground_map[(cg_row.provider_id, cg_row.id)] = cg_row

    # Gather names and result counts
    response_items: list[ScanResponse] = []
    for scan in scans:
        cg_record = campground_map.get(
            (scan.target.provider_id, scan.target.campground_id)
        )
        cg_name = cg_record.name if cg_record else ""
        ra_name = (
            cg_record.recreation_area.name
            if cg_record and cg_record.recreation_area
            else ""
        )

        # Count unique campsite IDs found in the latest scan_results
        found = (
            len({r.campsite_id for r in (scan.target.scan_results or [])})
            if scan.target.scan_results
            else 0
        )

        response_items.append(
            await _scan_to_response(
                scan,
                campground_name=cg_name,
                rec_area_name=ra_name,
                found_count=found,
            )
        )

    # Total count for pagination
    count_result = await session.execute(
        select(func.count(UserScanDB.id)).where(UserScanDB.user_id == current_user.id)
    )
    total = count_result.scalar_one()

    return ScanListResponse(scans=response_items, total=total)


# ---------------------------------------------------------------------------
# POST  /scans
# ---------------------------------------------------------------------------


@scan_router.post("", status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ScanResponse:
    """Create a new scan for the authenticated user.

    If a ``UniqueTarget`` with the same hash already exists it is re-used
    (de-duplication).  Otherwise a new target is created.
    """

    # Validate that the campground exists
    campground_db = await _lookup_campground(
        session, body.provider_id, body.campground_id
    )
    if campground_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campground {body.campground_id!r} not found for provider {body.provider_id}",
        )

    # Check / create unique target (de-duplication)
    target_hash = UniqueTargetDB.calculate_hash(
        body.provider_id, body.campground_id, body.start_date, body.end_date
    )
    result = await session.execute(
        select(UniqueTargetDB).where(UniqueTargetDB.hash == target_hash)
    )
    target = result.scalar_one_or_none()
    if target is None:
        target = UniqueTargetDB(
            provider_id=body.provider_id,
            campground_id=body.campground_id,
            start_date=body.start_date,
            end_date=body.end_date,
        )
        session.add(target)
        await session.flush()  # get the generated UUID and hash

    # Check for duplicate scan (same user + same target)
    existing = await session.execute(
        select(UserScanDB).where(
            UserScanDB.user_id == current_user.id,
            UserScanDB.target_id == target.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scan for this campground and date range already exists",
        )

    user_scan = UserScanDB(
        user_id=current_user.id,
        target_id=target.id,
        min_stay_length=body.min_stay_length,
        preferred_types=body.preferred_types,
        require_electric=body.require_electric,
    )
    session.add(user_scan)
    await session.commit()
    await session.refresh(user_scan)

    return await _scan_to_response(
        user_scan,
        campground_name=campground_db.name,
        rec_area_name=campground_db.recreation_area.name
        if campground_db.recreation_area
        else "",
    )


# ---------------------------------------------------------------------------
# GET  /scans/{id}
# ---------------------------------------------------------------------------


@scan_router.get("/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ScanDetailResponse:
    """Return detailed information for a single scan, including recent results."""

    result = await session.execute(
        select(UserScanDB)
        .options(
            joinedload(UserScanDB.target).joinedload(UniqueTargetDB.scan_results),
        )
        .where(UserScanDB.id == scan_id, UserScanDB.user_id == current_user.id)
    )
    scan = result.unique().scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    cg = await _lookup_campground(
        session, scan.target.provider_id, scan.target.campground_id
    )

    # Build result items
    results_raw = scan.target.scan_results or []
    seen: dict[str, list[str]] = {}
    for sr in results_raw:
        seen.setdefault(sr.campsite_id, []).extend(sr.available_dates or [])

    result_items = [
        ScanResultItem(
            campsite_id=campsite_id,
            available_dates=sorted(set(available_dates)),
        )
        for campsite_id, available_dates in seen.items()
    ]

    return ScanDetailResponse(
        id=scan.id,
        provider_id=scan.target.provider_id,
        campground_id=scan.target.campground_id,
        campground_name=cg.name if cg else "",
        recreation_area_name=cg.recreation_area.name
        if cg and cg.recreation_area
        else "",
        start_date=scan.target.start_date,
        end_date=scan.target.end_date,
        is_active=scan.is_active,
        min_stay_length=scan.min_stay_length,
        preferred_types=scan.preferred_types or [],
        require_electric=scan.require_electric,
        last_checked_at=scan.target.last_checked_at,
        found_count=len(result_items),
        created_at=scan.created_at,
        results=result_items,
    )


# ---------------------------------------------------------------------------
# PATCH  /scans/{id}
# ---------------------------------------------------------------------------


@scan_router.patch("/{scan_id}")
async def update_scan(
    scan_id: uuid.UUID,
    body: ScanUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ScanResponse:
    """Update scan filters or toggle ``is_active``."""

    result = await session.execute(
        select(UserScanDB)
        .options(joinedload(UserScanDB.target))
        .where(UserScanDB.id == scan_id, UserScanDB.user_id == current_user.id)
    )
    scan = result.unique().scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    if body.is_active is not None:
        scan.is_active = body.is_active
    if body.min_stay_length is not None:
        scan.min_stay_length = body.min_stay_length
    if body.preferred_types is not None:
        scan.preferred_types = body.preferred_types
    if body.require_electric is not None:
        scan.require_electric = body.require_electric

    await session.commit()
    await session.refresh(scan)

    cg = await _lookup_campground(
        session, scan.target.provider_id, scan.target.campground_id
    )

    return await _scan_to_response(
        scan,
        campground_name=cg.name if cg else "",
        rec_area_name=cg.recreation_area.name if cg and cg.recreation_area else "",
    )


# ---------------------------------------------------------------------------
# DELETE  /scans/{id}
# ---------------------------------------------------------------------------


@scan_router.delete("/{scan_id}")
async def delete_scan(
    scan_id: uuid.UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> Response:
    """Delete (unsubscribe from) a scan."""

    result = await session.execute(
        select(UserScanDB).where(
            UserScanDB.id == scan_id, UserScanDB.user_id == current_user.id
        )
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    await session.delete(scan)
    await session.commit()
    logger.info(
        "Scan deleted",
        scan_id=str(scan_id),
        user_id=str(current_user.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
