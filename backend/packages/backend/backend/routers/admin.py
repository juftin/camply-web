"""
Admin Router — ``/api/admin`` endpoints.

Endpoints for managing users, scans, shared targets, overview metrics,
and viewing administration audit events.
All endpoints require the ``require_admin`` dependency.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import (
    String,
    and_,
    case,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.elements import ColumnElement

from backend.auth import AdminUserDep, hash_password
from backend.config import AuthMode, backend_config
from backend.dependencies import SessionDep
from backend.metrics import USERS_CREATED_TOTAL
from backend.schemas import (
    AdminAuditEventItem,
    AdminAuditListResponse,
    AdminOperationsResponse,
    AdminOperationsTaskDetail,
    AdminOperationsTasksResponse,
    AdminOverviewResponse,
    AdminScanDetailResponse,
    AdminScanItem,
    AdminScanListResponse,
    AdminScanUpdateRequest,
    AdminTargetDetailResponse,
    AdminTargetSubscriberItem,
    AdminTrendsResponse,
    AdminUserCreateRequest,
    AdminUserDetailResponse,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    ScanResultItem,
)
from backend.services.operations import (
    get_operations_overview,
    get_recent_tasks,
    get_task_detail,
)
from backend.services.trends import get_admin_trends
from db.eligibility import eligible_scan_condition, is_scan_eligible
from db.models import (
    AdminAuditEvent,
    Campground,
    ScanResult,
    UniqueTarget,
    User,
    UserScan,
)

logger = structlog.getLogger(__name__)

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def _get_target_grace_period_seconds() -> int:
    """Return cooldown plus 2 discovery intervals (staleness threshold)."""
    return backend_config.target_cooldown + (2 * backend_config.heartbeat_interval)


def _target_status_condition(
    target_status: Literal["active", "overdue", "dormant"],
) -> ColumnElement[bool]:
    """Filter targets by subscriber eligibility and the same overdue grace period as overview."""
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
        seconds=_get_target_grace_period_seconds()
    )
    eligible_target_ids = (
        select(UserScan.target_id)
        .join(User)
        .where(eligible_scan_condition())
        .correlate(None)
    )
    has_subscriber = UniqueTarget.id.in_(eligible_target_ids)
    overdue = or_(
        and_(UniqueTarget.last_checked_at.is_(None), UniqueTarget.created_at < cutoff),
        and_(
            UniqueTarget.last_checked_at.is_not(None),
            UniqueTarget.last_checked_at < cutoff,
        ),
    )
    if target_status == "dormant":
        return ~has_subscriber
    return and_(has_subscriber, overdue if target_status == "overdue" else ~overdue)


async def _lookup_campgrounds_map(
    session: AsyncSession,
    keys: set[tuple[int, str]],
) -> dict[tuple[int, str], Campground]:
    """Batch-lookup campgrounds by (provider_id, campground_id)."""
    if not keys:
        return {}
    campground_ids = {cid for _, cid in keys}
    stmt = (
        select(Campground)
        .options(joinedload(Campground.recreation_area))
        .where(Campground.id.in_(campground_ids))
    )
    result = await session.execute(stmt)
    cgs = result.unique().scalars().all()
    return {(cg.provider_id, cg.id): cg for cg in cgs}


# ===========================================================================
# 1. GET /api/admin/overview
# ===========================================================================


@admin_router.get("/overview")
async def get_overview(
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminOverviewResponse:
    """
    Return global aggregates and overdue target counts.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cutoff = now - datetime.timedelta(seconds=_get_target_grace_period_seconds())

    # Total users & scanning enabled users
    u_stmt = select(
        func.count(User.id),
        func.count(case((User.scanning_enabled.is_(True), 1))),
    )
    u_res = await session.execute(u_stmt)
    total_users, scanning_enabled_users = u_res.one()

    # Total scans, saved active scans, and eligible scans
    s_stmt = select(
        func.count(UserScan.id),
        func.count(case((UserScan.is_active.is_(True), 1))),
        func.count(
            case(
                (
                    and_(User.scanning_enabled.is_(True), UserScan.is_active.is_(True)),
                    1,
                )
            )
        ),
    ).join(User, User.id == UserScan.user_id)
    s_res = await session.execute(s_stmt)
    total_scans, saved_active_scans, eligible_scans = s_res.one()

    # Total targets
    t_tot_stmt = select(func.count(UniqueTarget.id))
    total_targets = (await session.execute(t_tot_stmt)).scalar() or 0

    # Eligible targets (distinct targets with >= 1 eligible subscriber)
    elig_targets_subquery = (
        select(UniqueTarget.id)
        .join(UserScan, UserScan.target_id == UniqueTarget.id)
        .join(User, User.id == UserScan.user_id)
        .where(eligible_scan_condition())
        .distinct()
        .subquery()
    )
    elig_targets_stmt = select(func.count()).select_from(elig_targets_subquery)
    eligible_targets = (await session.execute(elig_targets_stmt)).scalar() or 0

    # Overdue targets: eligible targets whose last_checked_at is older than cutoff (or never checked and created before cutoff)
    overdue_stmt = (
        select(func.count(func.distinct(UniqueTarget.id)))
        .join(UserScan, UserScan.target_id == UniqueTarget.id)
        .join(User, User.id == UserScan.user_id)
        .where(
            eligible_scan_condition(),
            or_(
                and_(
                    UniqueTarget.last_checked_at.is_(None),
                    UniqueTarget.created_at < cutoff,
                ),
                and_(
                    UniqueTarget.last_checked_at.is_not(None),
                    UniqueTarget.last_checked_at < cutoff,
                ),
            ),
        )
    )
    overdue_targets = (await session.execute(overdue_stmt)).scalar() or 0

    return AdminOverviewResponse(
        total_users=total_users or 0,
        scanning_enabled_users=scanning_enabled_users or 0,
        total_scans=total_scans or 0,
        saved_active_scans=saved_active_scans or 0,
        eligible_scans=eligible_scans or 0,
        total_targets=total_targets,
        eligible_targets=eligible_targets,
        overdue_targets=overdue_targets,
        suspended_users=(total_users or 0) - (scanning_enabled_users or 0),
        dormant_targets=total_targets - eligible_targets,
        heartbeat_interval_seconds=backend_config.heartbeat_interval,
        target_cooldown_seconds=backend_config.target_cooldown,
        overdue_threshold_seconds=_get_target_grace_period_seconds(),
    )


# ===========================================================================
# 2. GET /api/admin/users
# ===========================================================================


@admin_router.get("/users")
async def list_users(
    admin: AdminUserDep,
    session: SessionDep,
    search: Optional[str] = Query(default=None),
    scanning_enabled: Optional[bool] = Query(default=None),
    is_invited: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminUserListResponse:
    """
    List, search, and filter users for administration.
    """
    conditions = []
    if search:
        search_term = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.email.ilike(search_term),
                cast(User.id, String).ilike(search_term),
            )
        )
    if scanning_enabled is not None:
        conditions.append(User.scanning_enabled == scanning_enabled)
    if is_invited is not None:
        conditions.append(User.is_invited == is_invited)

    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if conditions:
        stmt = stmt.where(and_(*conditions))
        count_stmt = count_stmt.where(and_(*conditions))

    total = (await session.execute(count_stmt)).scalar() or 0

    users_stmt = (
        stmt.order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    users = (await session.execute(users_stmt)).scalars().all()

    # Batch scan counts per user
    user_ids = [u.id for u in users]
    scan_counts: dict[uuid.UUID, tuple[int, int]] = {}
    if user_ids:
        sc_stmt = (
            select(
                UserScan.user_id,
                func.count(UserScan.id),
                func.count(case((UserScan.is_active.is_(True), 1))),
            )
            .where(UserScan.user_id.in_(user_ids))
            .group_by(UserScan.user_id)
        )
        for uid, total_s, active_s in (await session.execute(sc_stmt)).all():
            scan_counts[uid] = (total_s or 0, active_s or 0)

    items = [
        AdminUserItem(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            is_invited=u.is_invited,
            scanning_enabled=u.scanning_enabled,
            has_pushover_token=bool(u.pushover_token),
            must_change_password=u.must_change_password,
            total_scans=scan_counts.get(u.id, (0, 0))[0],
            active_scans=scan_counts.get(u.id, (0, 0))[1],
            created_at=u.created_at,
        )
        for u in users
    ]

    return AdminUserListResponse(users=items, total=total)


# ===========================================================================
# 3. POST /api/admin/users
# ===========================================================================


@admin_router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminUserCreateRequest,
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminUserDetailResponse:
    """
    Create a new user and assign them an initial password in session auth mode.
    """
    if backend_config.auth_mode != AuthMode.SESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation with password is only supported in session auth mode",
        )

    email = body.email.strip().lower()
    existing = (
        await session.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_user = User(
        email=email,
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
        must_change_password=body.must_change_password,
        is_invited=body.is_invited,
        scanning_enabled=body.scanning_enabled,
    )
    session.add(new_user)
    await session.flush()

    audit = AdminAuditEvent(
        actor_id=admin.id,
        action="user.create",
        subject_type="user",
        subject_id=new_user.id,
        prev_value=None,
        new_value=None,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(new_user)

    try:
        USERS_CREATED_TOTAL.inc()
    except Exception:
        pass

    return AdminUserDetailResponse(
        id=new_user.id,
        email=new_user.email,
        auth0_id=new_user.auth0_id,
        is_admin=new_user.is_admin,
        is_invited=new_user.is_invited,
        scanning_enabled=new_user.scanning_enabled,
        has_pushover_token=bool(new_user.pushover_token),
        must_change_password=new_user.must_change_password,
        total_scans=0,
        active_scans=0,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
    )


# ===========================================================================
# 4. GET /api/admin/users/{id}
# ===========================================================================


@admin_router.get("/users/{user_id}")
async def get_user_detail(
    user_id: uuid.UUID,
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminUserDetailResponse:
    """
    Get detailed user information and scan stats.
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    sc_stmt = select(
        func.count(UserScan.id),
        func.count(case((UserScan.is_active.is_(True), 1))),
    ).where(UserScan.user_id == user.id)
    total_s, active_s = (await session.execute(sc_stmt)).one()

    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        auth0_id=user.auth0_id,
        is_admin=user.is_admin,
        is_invited=user.is_invited,
        scanning_enabled=user.scanning_enabled,
        has_pushover_token=bool(user.pushover_token),
        must_change_password=user.must_change_password,
        total_scans=total_s or 0,
        active_scans=active_s or 0,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ===========================================================================
# 5. PATCH /api/admin/users/{id}
# ===========================================================================


@admin_router.patch("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdateRequest,
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminUserDetailResponse:
    """
    Update a user's scanning access or credentials and record audit events.
    """
    user_stmt = select(User).where(User.id == user_id).with_for_update()
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if body.is_admin is not None and body.is_admin != user.is_admin:
        if user.id == admin.id and not body.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own administrator privileges.",
            )
        prev_admin = user.is_admin
        user.is_admin = body.is_admin
        session.add(
            AdminAuditEvent(
                actor_id=admin.id,
                action="user.is_admin",
                subject_type="user",
                subject_id=user.id,
                prev_value=prev_admin,
                new_value=body.is_admin,
            )
        )

    if body.scanning_enabled is not None:
        prev_val = user.scanning_enabled
        user.scanning_enabled = body.scanning_enabled
        session.add(
            AdminAuditEvent(
                actor_id=admin.id,
                action="user.scanning_enabled",
                subject_type="user",
                subject_id=user.id,
                prev_value=prev_val,
                new_value=body.scanning_enabled,
            )
        )

    if body.must_change_password is not None:
        prev_mcp = user.must_change_password
        user.must_change_password = body.must_change_password
        session.add(
            AdminAuditEvent(
                actor_id=admin.id,
                action="user.must_change_password",
                subject_type="user",
                subject_id=user.id,
                prev_value=prev_mcp,
                new_value=body.must_change_password,
            )
        )

    if body.password is not None:
        if backend_config.auth_mode != AuthMode.SESSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password management is only supported in session auth mode.",
            )
        user.password_hash = hash_password(body.password)
        if body.must_change_password is not None:
            user.must_change_password = body.must_change_password
        else:
            user.must_change_password = True
        session.add(
            AdminAuditEvent(
                actor_id=admin.id,
                action="user.password_reset",
                subject_type="user",
                subject_id=user.id,
                prev_value=None,
                new_value=None,
            )
        )

    await session.commit()
    await session.refresh(user)

    sc_stmt = select(
        func.count(UserScan.id),
        func.count(case((UserScan.is_active.is_(True), 1))),
    ).where(UserScan.user_id == user.id)
    total_s, active_s = (await session.execute(sc_stmt)).one()

    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        auth0_id=user.auth0_id,
        is_admin=user.is_admin,
        is_invited=user.is_invited,
        scanning_enabled=user.scanning_enabled,
        has_pushover_token=bool(user.pushover_token),
        must_change_password=user.must_change_password,
        total_scans=total_s or 0,
        active_scans=active_s or 0,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ===========================================================================
# 5. GET /api/admin/scans
# ===========================================================================


@admin_router.get("/scans")
async def list_admin_scans(
    admin: AdminUserDep,
    session: SessionDep,
    owner_id: Optional[uuid.UUID] = Query(default=None),
    provider_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    is_eligible: Optional[bool] = Query(default=None),
    target_status: Optional[Literal["active", "overdue", "dormant"]] = Query(
        default=None
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminScanListResponse:
    """
    List and filter scans across all users.
    """
    conditions = []
    if owner_id is not None:
        conditions.append(UserScan.user_id == owner_id)
    if provider_id is not None:
        conditions.append(UniqueTarget.provider_id == provider_id)
    if is_active is not None:
        conditions.append(UserScan.is_active == is_active)
    if is_eligible is True:
        conditions.append(eligible_scan_condition())
    elif is_eligible is False:
        conditions.append(
            or_(
                User.scanning_enabled.is_(False),
                UserScan.is_active.is_(False),
            )
        )

    if target_status is not None:
        conditions.append(_target_status_condition(target_status))

    base_query = (
        select(UserScan)
        .join(User, User.id == UserScan.user_id)
        .join(UniqueTarget, UniqueTarget.id == UserScan.target_id)
        .options(
            joinedload(UserScan.user),
            joinedload(UserScan.target),
        )
    )
    count_query = (
        select(func.count(UserScan.id))
        .join(User, User.id == UserScan.user_id)
        .join(UniqueTarget, UniqueTarget.id == UserScan.target_id)
    )

    if conditions:
        base_query = base_query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total = (await session.execute(count_query)).scalar() or 0

    scans_stmt = (
        base_query.order_by(UserScan.created_at.desc(), UserScan.id.desc())
        .offset(offset)
        .limit(limit)
    )
    scans = (await session.execute(scans_stmt)).unique().scalars().all()

    # Batch campgrounds
    cg_keys = {(s.target.provider_id, s.target.campground_id) for s in scans}
    cg_map = await _lookup_campgrounds_map(session, cg_keys)

    result_counts: dict[uuid.UUID, int] = dict(
        (
            await session.execute(
                select(
                    ScanResult.target_id,
                    func.count(func.distinct(ScanResult.campsite_id)),
                )
                .where(ScanResult.target_id.in_({s.target_id for s in scans}))
                .group_by(ScanResult.target_id)
            )
        )
        .tuples()
        .all()
    )

    items: list[AdminScanItem] = []
    for s in scans:
        cg_obj = cg_map.get((s.target.provider_id, s.target.campground_id))
        items.append(
            AdminScanItem(
                id=s.id,
                user_id=s.user_id,
                user_email=s.user.email,
                target_id=s.target_id,
                provider_id=s.target.provider_id,
                campground_id=s.target.campground_id,
                campground_name=cg_obj.name if cg_obj is not None else "",
                start_date=s.target.start_date,
                end_date=s.target.end_date,
                is_active=s.is_active,
                is_eligible=is_scan_eligible(s.user.scanning_enabled, s.is_active),
                user_scanning_enabled=s.user.scanning_enabled,
                last_checked_at=s.target.last_checked_at,
                found_count=result_counts.get(s.target_id, 0),
                created_at=s.created_at,
            )
        )

    return AdminScanListResponse(scans=items, total=total)


# ===========================================================================
# 6. GET /api/admin/scans/{id}
# ===========================================================================


@admin_router.get("/scans/{scan_id}")
async def get_admin_scan(
    scan_id: uuid.UUID,
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminScanDetailResponse:
    """
    Get detailed information for a single scan.
    """
    stmt = (
        select(UserScan)
        .options(
            joinedload(UserScan.user),
            joinedload(UserScan.target).joinedload(UniqueTarget.scan_results),
        )
        .where(UserScan.id == scan_id)
    )
    scan = (await session.execute(stmt)).unique().scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    cg_map = await _lookup_campgrounds_map(
        session, {(scan.target.provider_id, scan.target.campground_id)}
    )
    cg = cg_map.get((scan.target.provider_id, scan.target.campground_id))

    # Build result items
    results_raw = scan.target.scan_results or []
    seen: dict[str, list[str]] = {}
    for sr in results_raw:
        seen.setdefault(sr.campsite_id, []).extend(sr.available_dates or [])

    result_items = [
        ScanResultItem(
            campsite_id=cid,
            available_dates=sorted(set(dates)),
        )
        for cid, dates in seen.items()
    ]

    return AdminScanDetailResponse(
        id=scan.id,
        user_id=scan.user_id,
        user_email=scan.user.email,
        target_id=scan.target_id,
        provider_id=scan.target.provider_id,
        campground_id=scan.target.campground_id,
        campground_name=cg.name if cg else "",
        recreation_area_name=(
            cg.recreation_area.name if cg and cg.recreation_area else ""
        ),
        start_date=scan.target.start_date,
        end_date=scan.target.end_date,
        is_active=scan.is_active,
        is_eligible=is_scan_eligible(scan.user.scanning_enabled, scan.is_active),
        user_scanning_enabled=scan.user.scanning_enabled,
        min_stay_length=scan.min_stay_length,
        preferred_types=scan.preferred_types or [],
        require_electric=scan.require_electric,
        last_checked_at=scan.target.last_checked_at,
        created_at=scan.created_at,
        results=result_items,
    )


# ===========================================================================
# 7. PATCH /api/admin/scans/{id}
# ===========================================================================


@admin_router.patch("/scans/{scan_id}")
async def update_admin_scan(
    scan_id: uuid.UUID,
    body: AdminScanUpdateRequest,
    admin: AdminUserDep,
    session: SessionDep,
) -> AdminScanDetailResponse:
    """
    Toggle is_active for a scan and record an audit event.
    """
    stmt = (
        select(UserScan)
        .options(
            joinedload(UserScan.user),
            joinedload(UserScan.target).joinedload(UniqueTarget.scan_results),
        )
        .where(UserScan.id == scan_id)
        .with_for_update()
    )
    scan = (await session.execute(stmt)).unique().scalar_one_or_none()
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found",
        )

    # If resuming, check whether user has scanning enabled
    if body.is_active is True and not scan.user.scanning_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ERR_SCANNING_DISABLED",
                "message": "Scanning is disabled for this user. Cannot resume scan.",
            },
        )

    prev_val = scan.is_active
    scan.is_active = body.is_active

    audit = AdminAuditEvent(
        actor_id=admin.id,
        action="scan.is_active",
        subject_type="scan",
        subject_id=scan.id,
        prev_value=prev_val,
        new_value=body.is_active,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(scan)

    cg_map = await _lookup_campgrounds_map(
        session, {(scan.target.provider_id, scan.target.campground_id)}
    )
    cg = cg_map.get((scan.target.provider_id, scan.target.campground_id))

    results_raw = scan.target.scan_results or []
    seen: dict[str, list[str]] = {}
    for sr in results_raw:
        seen.setdefault(sr.campsite_id, []).extend(sr.available_dates or [])

    result_items = [
        ScanResultItem(
            campsite_id=cid,
            available_dates=sorted(set(dates)),
        )
        for cid, dates in seen.items()
    ]

    return AdminScanDetailResponse(
        id=scan.id,
        user_id=scan.user_id,
        user_email=scan.user.email,
        target_id=scan.target_id,
        provider_id=scan.target.provider_id,
        campground_id=scan.target.campground_id,
        campground_name=cg.name if cg else "",
        recreation_area_name=(
            cg.recreation_area.name if cg and cg.recreation_area else ""
        ),
        start_date=scan.target.start_date,
        end_date=scan.target.end_date,
        is_active=scan.is_active,
        is_eligible=is_scan_eligible(scan.user.scanning_enabled, scan.is_active),
        user_scanning_enabled=scan.user.scanning_enabled,
        min_stay_length=scan.min_stay_length,
        preferred_types=scan.preferred_types or [],
        require_electric=scan.require_electric,
        last_checked_at=scan.target.last_checked_at,
        created_at=scan.created_at,
        results=result_items,
    )


# ===========================================================================
# 8. GET /api/admin/targets/{id}
# ===========================================================================


@admin_router.get("/targets/{target_id}")
async def get_admin_target(
    target_id: uuid.UUID,
    admin: AdminUserDep,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminTargetDetailResponse:
    """
    Get detailed information for a shared unique target and its subscribers.
    """
    stmt = select(UniqueTarget).where(UniqueTarget.id == target_id)
    target = (await session.execute(stmt)).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target not found",
        )

    cg_map = await _lookup_campgrounds_map(
        session, {(target.provider_id, target.campground_id)}
    )
    cg = cg_map.get((target.provider_id, target.campground_id))

    # Count subscribers
    sub_count_stmt = (
        select(
            func.count(UserScan.id),
            func.count(
                case(
                    (
                        and_(
                            User.scanning_enabled.is_(True),
                            UserScan.is_active.is_(True),
                        ),
                        1,
                    )
                )
            ),
        )
        .join(User, User.id == UserScan.user_id)
        .where(UserScan.target_id == target.id)
    )
    total_subs, elig_subs = (await session.execute(sub_count_stmt)).one()
    total_subscribers = total_subs or 0
    eligible_subscribers = elig_subs or 0

    # Determine status: dormant, overdue, or active
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    cutoff = now - datetime.timedelta(seconds=_get_target_grace_period_seconds())
    target_status: Literal["active", "overdue", "dormant"]
    last_check = target.last_checked_at or target.created_at
    if last_check.tzinfo is None:
        last_check = last_check.replace(tzinfo=datetime.timezone.utc)
    if eligible_subscribers == 0:
        target_status = "dormant"
    elif last_check < cutoff:
        target_status = "overdue"
    else:
        target_status = "active"

    # Paginated subscribers
    subs_stmt = (
        select(UserScan)
        .options(joinedload(UserScan.user))
        .where(UserScan.target_id == target.id)
        .order_by(UserScan.created_at.desc(), UserScan.id.desc())
        .offset(offset)
        .limit(limit)
    )
    sub_scans = (await session.execute(subs_stmt)).unique().scalars().all()

    subscriber_items = [
        AdminTargetSubscriberItem(
            scan_id=s.id,
            user_id=s.user_id,
            user_email=s.user.email,
            is_active=s.is_active,
            is_eligible=is_scan_eligible(s.user.scanning_enabled, s.is_active),
            user_scanning_enabled=s.user.scanning_enabled,
            created_at=s.created_at,
        )
        for s in sub_scans
    ]

    return AdminTargetDetailResponse(
        id=target.id,
        provider_id=target.provider_id,
        campground_id=target.campground_id,
        campground_name=cg.name if cg else "",
        start_date=target.start_date,
        end_date=target.end_date,
        hash=target.hash,
        last_checked_at=target.last_checked_at,
        created_at=target.created_at,
        total_subscribers=total_subscribers,
        eligible_subscribers=eligible_subscribers,
        status=target_status,
        overdue_threshold_seconds=_get_target_grace_period_seconds(),
        subscribers=subscriber_items,
        subscribers_total=total_subscribers,
    )


# ===========================================================================
# 9. GET /api/admin/audit
# ===========================================================================


@admin_router.get("/audit")
async def list_admin_audit(
    admin: AdminUserDep,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminAuditListResponse:
    """
    Paginated audit log of administrator actions.
    """
    count_stmt = select(func.count(AdminAuditEvent.id))
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(AdminAuditEvent)
        .options(joinedload(AdminAuditEvent.actor))
        .order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    )
    events = (await session.execute(stmt)).unique().scalars().all()

    items = [
        AdminAuditEventItem(
            id=e.id,
            actor_id=e.actor_id,
            actor_email=e.actor.email if e.actor else "system@camply.local",
            action=e.action,
            subject_type=e.subject_type,
            subject_id=e.subject_id,
            prev_value=e.prev_value,
            new_value=e.new_value,
            created_at=e.created_at,
        )
        for e in events
    ]

    return AdminAuditListResponse(events=items, total=total)


# ===========================================================================
# Operations Inspection
# ===========================================================================


@admin_router.get("/operations")
async def get_admin_operations(
    admin: AdminUserDep,
) -> AdminOperationsResponse:
    """
    Overview of Celery worker execution nodes, queue depth, and discovery status.
    """
    return await get_operations_overview()


@admin_router.get("/operations/tasks")
async def list_admin_operations_tasks(
    admin: AdminUserDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    task_name: Optional[str] = Query(default=None),
    outcome: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> AdminOperationsTasksResponse:
    """
    Paginated recent task executions from the Valkey telemetry stream.
    """
    return await get_recent_tasks(
        limit=limit,
        offset=offset,
        task_name=task_name,
        outcome=outcome,
        provider=provider,
        search=search,
    )


@admin_router.get("/operations/tasks/{task_id}")
async def get_admin_operations_task_detail(
    task_id: str,
    admin: AdminUserDep,
) -> AdminOperationsTaskDetail:
    """
    Detailed metadata for a single task execution.
    """
    item = await get_task_detail(task_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in telemetry history",
        )
    return item


# ===========================================================================
# Trends & Metrics Proxy
# ===========================================================================


@admin_router.get("/trends")
async def get_trends(
    admin: AdminUserDep,
    group: str = Query(default="usage", pattern="^(usage|api|worker|provider)$"),
    range: str = Query(default="24h", pattern="^(24h|7d|30d)$"),
    endpoint: Optional[str] = Query(default=None),
    task_name: Optional[str] = Query(default=None),
    provider: Optional[str] = Query(default=None),
) -> AdminTrendsResponse:
    """
    Historical metrics and operational trends proxied from Prometheus.
    """
    return await get_admin_trends(
        group=group,
        range_param=range,
        endpoint_filter=endpoint,
        task_name_filter=task_name,
        provider_filter=provider,
    )
