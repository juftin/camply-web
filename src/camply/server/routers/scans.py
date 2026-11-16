"""
Scan management router — ``/api/scans`` endpoints.

All endpoints are auth-gated through the ``CurrentUserDep`` dependency:

* **none mode** — the configured admin is automatically logged in.
* **session mode** — an in-app password login establishes a session cookie.
* **invite-only** — uninvited users cannot manage scans when enabled.
* **auth0 mode** — a valid ``Authorization: Bearer <JWT>`` header is required;
  users are upserted into the database automatically.
"""

from __future__ import annotations

import datetime
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError

from camply.db.availability import matching_scan_results, validate_scan_dates
from camply.db.coverage import (
    definition_hash,
    eligible_members,
    get_or_create_target,
    live_targets,
    normalized_choices,
    reconcile_coverage,
    scan_load_options,
)
from camply.db.models import (
    Campground as CampgroundDB,
)
from camply.db.models import NotificationOutbox, Provider, RecreationArea
from camply.db.models import (
    User as UserDB,
)
from camply.db.models import (
    UserScan as UserScanDB,
)
from camply.providers import PROVIDERS, get_provider_filter_capabilities
from camply.server.auth import (
    CurrentUserDep,
    require_invitation,
    require_password_not_expired,
)
from camply.server.dependencies import SessionDep
from camply.server.metrics import SCANS_CREATED_TOTAL
from camply.server.schemas import (
    ScanCampgroundItem,
    ScanChoiceItem,
    ScanCreateRequest,
    ScanDetailResponse,
    ScanListResponse,
    ScanResponse,
    ScanResultItem,
    ScanUpdateRequest,
)

logger = structlog.getLogger(__name__)


scan_router = APIRouter(
    prefix="/scans",
    tags=["scans"],
    dependencies=[Depends(require_invitation), Depends(require_password_not_expired)],
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


def _members(scan: UserScanDB) -> list[ScanCampgroundItem]:
    """Describe live coverage and retain unavailable fixed selections."""
    targets = live_targets(scan)
    links = {link.target_id: link for link in scan.coverage}
    rows = []
    for target in targets:
        cg = target.campground
        link = links.get(target.id)
        rows.append(
            ScanCampgroundItem(
                provider_id=target.provider_id,
                campground_id=target.campground_id,
                campground_name=cg.name if cg else scan.destination_name,
                eligible=True,
                target_id=target.id,
                outcome=link.outcome if link else "pending",
                last_checked_at=target.last_checked_at,
                attempt_started_at=target.attempt_started_at,
                error_category=target.attempt_error_category,
            )
        )
    eligible_ids = {target.campground_id for target in targets}
    for item in scan.selected_campgrounds or []:
        if item["id"] not in eligible_ids:
            rows.append(
                ScanCampgroundItem(
                    provider_id=scan.provider_id,
                    campground_id=item["id"],
                    campground_name=item["name"],
                    eligible=False,
                    unavailable_reason="Campground is no longer eligible in this recreation area",
                )
            )
    return rows


async def _scan_to_response(scan: UserScanDB, **unused: object) -> ScanResponse:
    """Represent one saved definition with qualified, truthful coverage counts."""
    targets = live_targets(scan)
    matches = matching_scan_results(scan)
    rows = _members(scan)
    area = scan.destination_type == "recreation_area"
    cg = scan.target.campground if scan.target else None
    success = sum(row.eligible and row.outcome == "success" for row in rows)
    failed = sum(row.eligible and row.outcome == "failed" for row in rows)
    pending = len(targets) - success - failed
    coverage_status = (
        "no_eligible_campgrounds"
        if not targets
        else "partial"
        if failed or (success and pending)
        else "complete"
        if not pending
        else "checking"
        if scan.current_round_id
        else "waiting"
    )
    last = (
        scan.last_full_checked_at
        if area
        else scan.target.last_checked_at
        if scan.target
        else None
    )
    return ScanResponse(
        id=scan.id,
        provider_id=scan.provider_id,
        destination_type=scan.destination_type,
        destination_name=scan.destination_name,
        campground_id=scan.campground_id,
        campground_name=None if area else cg.name if cg else scan.destination_name,
        recreation_area_id=scan.recreation_area_id
        if area
        else cg.recreation_area_id
        if cg
        else None,
        recreation_area_name=scan.destination_name
        if area
        else cg.recreation_area.name
        if cg and cg.recreation_area
        else "",
        coverage_mode=scan.coverage_mode,
        campground_ids=[item["id"] for item in scan.selected_campgrounds or []],
        selected_campgrounds=[
            ScanChoiceItem(id=item["id"], name=item["name"])
            for item in scan.selected_campgrounds or []
        ],
        eligible_campground_count=len(targets),
        unavailable_selection_count=sum(not row.eligible for row in rows),
        matching_campground_count=len({result.target_id for result, _ in matches}),
        destination_available=bool(targets),
        coverage_status=coverage_status,
        checked_campground_count=success,
        failed_campground_count=failed,
        pending_campground_count=pending,
        last_full_checked_at=scan.last_full_checked_at,
        row_version=scan.row_version,
        start_date=scan.start_date,
        end_date=scan.end_date,
        is_active=scan.is_active,
        min_stay_length=scan.min_stay_length,
        preferred_types=scan.preferred_types or [],
        require_electric=scan.require_electric,
        require_accessible=scan.require_accessible,
        min_rv_length=scan.min_rv_length,
        allowed_weekdays=scan.allowed_weekdays or list(range(7)),
        last_checked_at=last,
        found_count=len(matches),
        created_at=scan.created_at,
    )


async def _load(
    session: AsyncSession, scan_id: uuid.UUID, user_id: uuid.UUID
) -> UserScanDB:
    """Load owned snapshots and catalog context without implicit async I/O."""
    scan = await session.scalar(
        select(UserScanDB)
        .options(*scan_load_options())
        .where(UserScanDB.id == scan_id, UserScanDB.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


_FILTER_LABELS: tuple[tuple[str, str], ...] = (
    ("preferred_types", "campsite type"),
    ("require_electric", "electric hookup"),
    ("require_accessible", "ADA accessibility"),
    ("min_rv_length", "minimum RV / trailer length"),
)


def _validate_provider_filter_support(
    *,
    provider_id: int,
    provider_name: str,
    preferred_types: list[str] | None,
    require_electric: bool,
    require_accessible: bool,
    min_rv_length: int | None,
    only_fields: set[str] | None = None,
) -> None:
    """Reject site-attribute filters unsupported by ``provider_id``."""
    caps = get_provider_filter_capabilities(provider_id)
    active_values: dict[str, bool] = {
        "preferred_types": bool(preferred_types),
        "require_electric": bool(require_electric),
        "require_accessible": bool(require_accessible),
        "min_rv_length": min_rv_length is not None,
    }
    unsupported = [
        label
        for field, label in _FILTER_LABELS
        if (only_fields is None or field in only_fields)
        and active_values[field]
        and not getattr(caps, field)
    ]
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{provider_name} does not support {', '.join(unsupported)} filtering."
            ),
        )


async def _validate_updated_scan_filters(
    session: AsyncSession,
    scan: UserScanDB,
    body: ScanUpdateRequest,
    definition_changed: bool,
) -> None:
    """Validate preference-only PATCH updates against provider filter support."""
    if definition_changed:
        return
    modified_filter_fields = body.model_fields_set & {
        field for field, _ in _FILTER_LABELS
    }
    if not modified_filter_fields:
        return
    provider_name = (
        await session.scalar(
            select(Provider.name).where(Provider.id == scan.provider_id)
        )
        or f"Provider {scan.provider_id}"
    )
    _validate_provider_filter_support(
        provider_id=scan.provider_id,
        provider_name=provider_name,
        preferred_types=scan.preferred_types,
        require_electric=scan.require_electric,
        require_accessible=scan.require_accessible,
        min_rv_length=scan.min_rv_length,
        only_fields=modified_filter_fields,
    )


def _assign_scan_preferences(scan: UserScanDB, body: ScanCreateRequest) -> None:
    """Copy site preferences from a validated create payload onto ``scan``."""
    scan.min_stay_length = body.min_stay_length
    scan.preferred_types = body.preferred_types
    scan.require_electric = body.require_electric
    scan.require_accessible = body.require_accessible
    scan.min_rv_length = body.min_rv_length
    scan.allowed_weekdays = (
        body.allowed_weekdays if body.allowed_weekdays != list(range(7)) else None
    )


def _apply_scan_preference_updates(scan: UserScanDB, body: ScanUpdateRequest) -> None:
    """Apply partial PATCH preference updates, distinguishing omission from ``None``."""
    for field in (
        "is_active",
        "min_stay_length",
        "preferred_types",
        "require_electric",
        "require_accessible",
    ):
        value = getattr(body, field)
        if value is not None:
            setattr(scan, field, value)
    if "min_rv_length" in body.model_fields_set:
        scan.min_rv_length = body.min_rv_length
    if "allowed_weekdays" in body.model_fields_set:
        scan.allowed_weekdays = (
            body.allowed_weekdays if body.allowed_weekdays != list(range(7)) else None
        )


async def _assign_definition(  # noqa: C901
    session: AsyncSession,
    scan: UserScanDB,
    body: ScanCreateRequest,
    *,
    retain_unavailable: bool = False,
) -> None:
    """Validate a complete definition atomically against confirmed catalog membership."""
    provider = await session.scalar(
        select(Provider).where(Provider.id == body.provider_id).with_for_update()
    )
    if provider is None or not provider.enabled:
        raise HTTPException(status_code=422, detail="Provider unavailable")
    _validate_provider_filter_support(
        provider_id=provider.id,
        provider_name=provider.name,
        preferred_types=body.preferred_types,
        require_electric=body.require_electric,
        require_accessible=body.require_accessible,
        min_rv_length=body.min_rv_length,
    )
    choices: list[dict[str, str]] = []
    target = None
    if body.destination_type == "campground":
        cg = await _lookup_campground(
            session, body.provider_id, body.campground_id or ""
        )
        if cg is None or not cg.enabled:
            raise HTTPException(
                status_code=404, detail="Campground not found for provider"
            )
        name = cg.name
        target = await get_or_create_target(
            session,
            provider_id=body.provider_id,
            campground_id=cg.id,
            start_date=body.start_date,
            end_date=body.end_date,
        )
    else:
        area = await session.get(
            RecreationArea, (body.recreation_area_id, body.provider_id)
        )
        if area is None:
            raise HTTPException(
                status_code=404, detail="Recreation area not found for provider"
            )
        if not area.enabled and not retain_unavailable:
            raise HTTPException(status_code=422, detail="Recreation area unavailable")
        name = area.name
        members = await eligible_members(
            session, provider_id=body.provider_id, area_id=body.recreation_area_id or ""
        )
        by_id = {member.id: member.name for member in members}
        if body.coverage_mode == "selected":
            try:
                ids = normalized_choices(body.campground_ids or [])
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            previous = (
                {item["id"]: item["name"] for item in scan.selected_campgrounds or []}
                if retain_unavailable
                else {}
            )
            if any(value not in by_id and value not in previous for value in ids):
                raise HTTPException(
                    status_code=422,
                    detail="Selected campground is not eligible in this recreation area",
                )
            choices = [
                {"id": value, "name": by_id.get(value, previous.get(value, value))}
                for value in ids
            ]
        if not members and not retain_unavailable:
            raise HTTPException(
                status_code=422,
                detail="No eligible campgrounds in this recreation area",
            )
    scan.provider_id = body.provider_id
    scan.destination_type = body.destination_type
    scan.campground_id = body.campground_id
    scan.recreation_area_id = body.recreation_area_id
    scan.destination_name = name
    scan.coverage_mode = body.coverage_mode
    scan.selected_campgrounds = choices
    scan.start_date, scan.end_date = body.start_date, body.end_date
    scan.target_id = target.id if target else None
    _assign_scan_preferences(scan, body)
    scan.definition_hash = definition_hash(
        provider_id=scan.provider_id,
        destination_type=scan.destination_type,
        destination_id=scan.recreation_area_id or scan.campground_id or "",
        start_date=scan.start_date,
        end_date=scan.end_date,
        coverage_mode=scan.coverage_mode,
        selected_ids=[item["id"] for item in choices],
    )
    duplicate = await session.scalar(
        select(UserScanDB.id).where(
            UserScanDB.user_id == scan.user_id,
            UserScanDB.definition_hash == scan.definition_hash,
            UserScanDB.id != scan.id,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="duplicate_scan: A scan for this destination and date range already exists",
        )


def _validate_scan_criteria(
    *,
    start_date: datetime.date,
    end_date: datetime.date,
    min_stay_length: int,
    allowed_weekdays: list[int] | None,
) -> None:
    """Translate impossible calendar combinations to actionable request errors."""
    try:
        validate_scan_dates(
            start_date=start_date,
            end_date=end_date,
            min_stay_length=min_stay_length,
            allowed_weekdays=allowed_weekdays,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@scan_router.get("")
async def list_scans(
    current_user: CurrentUserDep,
    session: SessionDep,
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ScanListResponse:
    """List saved subscriptions once, independent of resolved member count."""
    predicate = [UserScanDB.user_id == current_user.id]
    if is_active is not None:
        predicate.append(UserScanDB.is_active == is_active)
    scans = (
        (
            await session.scalars(
                select(UserScanDB)
                .options(*scan_load_options())
                .where(*predicate)
                .order_by(UserScanDB.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .unique()
        .all()
    )
    total = (
        await session.scalar(select(func.count(UserScanDB.id)).where(*predicate)) or 0
    )
    return ScanListResponse(
        scans=[await _scan_to_response(scan) for scan in scans], total=total
    )


@scan_router.post("", status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: ScanCreateRequest, current_user: CurrentUserDep, session: SessionDep
) -> ScanResponse:
    """Save one validated destination and its shared member links in one transaction."""
    user = await session.scalar(
        select(UserDB).where(UserDB.id == current_user.id).with_for_update()
    )
    if user is None or not user.scanning_enabled:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ERR_SCANNING_DISABLED",
                "message": "Scanning is currently disabled for this account.",
            },
        )
    scan = UserScanDB(
        id=uuid.uuid4(),
        user_id=user.id,
        coverage=[],
        definition_revision=1,
        coverage_revision=1,
        row_version=1,
    )
    _validate_scan_criteria(
        start_date=body.start_date,
        end_date=body.end_date,
        min_stay_length=body.min_stay_length,
        allowed_weekdays=body.allowed_weekdays,
    )
    await _assign_definition(session, scan, body)
    session.add(scan)
    try:
        await session.flush()
        # The compatibility insert hook already persisted campground links.
        await session.refresh(scan, ["coverage"])
        await reconcile_coverage(session, scan, bump_row_version=False)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="duplicate_scan: Scan definition already exists"
        ) from error
    SCANS_CREATED_TOTAL.inc()
    return await _scan_to_response(await _load(session, scan.id, user.id))


@scan_router.get("/{scan_id}")
async def get_scan(
    scan_id: uuid.UUID, current_user: CurrentUserDep, session: SessionDep
) -> ScanDetailResponse:
    """Return qualified matches and per-member freshness without provider requests."""
    scan = await _load(session, scan_id, current_user.id)
    targets = {target.id: target for target in live_targets(scan)}
    items = []
    for result, dates in matching_scan_results(scan):
        target = targets[result.target_id]
        cg = target.campground
        provider = PROVIDERS.get(target.provider_id)
        items.append(
            ScanResultItem(
                provider_id=target.provider_id,
                campground_id=target.campground_id,
                campground_name=cg.name if cg else "",
                campsite_id=result.campsite_id,
                campsite_name=result.campsite_name,
                campsite_type=result.campsite_type,
                is_electric=result.is_electric,
                is_accessible=result.is_accessible,
                permitted_equipment=result.permitted_equipment or [],
                max_vehicle_length=result.max_vehicle_length,
                available_dates=dates,
                booking_url=provider.get_campground_url(
                    campground_id=target.campground_id,
                    rec_area_id=cg.recreation_area_id if cg else None,
                )
                if provider
                else "",
                last_checked_at=target.last_checked_at,
                is_stale=target.attempt_error_category is not None,
            )
        )
    items.sort(
        key=lambda item: (
            item.campground_name.casefold(),
            item.campsite_name.casefold(),
            item.campsite_id,
        )
    )
    response = await _scan_to_response(scan)
    return ScanDetailResponse(
        **response.model_dump(), results=items, campgrounds=_members(scan)
    )


@scan_router.patch("/{scan_id}")
async def update_scan(
    scan_id: uuid.UUID,
    body: ScanUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ScanResponse:
    """Merge edits while retaining unavailable selections and isolating other users."""
    user = await session.scalar(
        select(UserDB).where(UserDB.id == current_user.id).with_for_update()
    )
    scan = await _load(session, scan_id, current_user.id)
    if body.row_version is not None and body.row_version != scan.row_version:
        raise HTTPException(
            status_code=409, detail="scan_changed: Reload and review the saved scan"
        )
    if body.is_active is True and (user is None or not user.scanning_enabled):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "ERR_SCANNING_DISABLED",
                "message": "Scanning is currently disabled for this account.",
            },
        )
    if body.model_fields_set & {
        "start_date",
        "end_date",
        "min_stay_length",
        "allowed_weekdays",
    }:
        _validate_scan_criteria(
            start_date=body.start_date or scan.start_date,
            end_date=body.end_date or scan.end_date,
            min_stay_length=body.min_stay_length or scan.min_stay_length,
            allowed_weekdays=body.allowed_weekdays
            if "allowed_weekdays" in body.model_fields_set
            else scan.allowed_weekdays,
        )
    definition_fields = {
        "provider_id",
        "destination_type",
        "campground_id",
        "recreation_area_id",
        "coverage_mode",
        "campground_ids",
        "start_date",
        "end_date",
    }
    if body.model_fields_set & definition_fields:
        kind = body.destination_type or scan.destination_type
        replacement = (
            (body.provider_id is not None and body.provider_id != scan.provider_id)
            or kind != scan.destination_type
            or (
                body.recreation_area_id is not None
                and body.recreation_area_id != scan.recreation_area_id
            )
        )
        if (
            replacement
            and (
                kind == "recreation_area" or scan.destination_type == "recreation_area"
            )
            and not {"destination_type", "provider_id"}.issubset(body.model_fields_set)
        ):
            raise HTTPException(
                status_code=422,
                detail="Destination replacement requires its complete destination variant",
            )
        mode = body.coverage_mode or (None if replacement else scan.coverage_mode)
        selected = (
            body.campground_ids
            if body.campground_ids is not None
            else [item["id"] for item in scan.selected_campgrounds or []]
            if not replacement and mode == "selected"
            else None
        )
        if (
            body.coverage_mode == "selected"
            and scan.coverage_mode != "selected"
            and body.campground_ids is None
        ):
            raise HTTPException(
                status_code=422,
                detail="Choose campgrounds explicitly for selected coverage",
            )
        values = {
            "provider_id": body.provider_id or scan.provider_id,
            "destination_type": kind,
            "campground_id": body.campground_id
            if body.campground_id is not None
            else scan.campground_id
            if not replacement
            else None,
            "recreation_area_id": body.recreation_area_id
            if body.recreation_area_id is not None
            else scan.recreation_area_id
            if not replacement
            else None,
            "coverage_mode": mode,
            "campground_ids": selected,
            "start_date": body.start_date or scan.start_date,
            "end_date": body.end_date or scan.end_date,
            "min_stay_length": body.min_stay_length or scan.min_stay_length,
            "preferred_types": body.preferred_types
            if body.preferred_types is not None
            else scan.preferred_types or [],
            "require_electric": body.require_electric
            if body.require_electric is not None
            else scan.require_electric,
            "require_accessible": body.require_accessible
            if body.require_accessible is not None
            else scan.require_accessible,
            "min_rv_length": body.min_rv_length
            if "min_rv_length" in body.model_fields_set
            else scan.min_rv_length,
            "allowed_weekdays": body.allowed_weekdays
            if "allowed_weekdays" in body.model_fields_set
            else (scan.allowed_weekdays or list(range(7))),
        }
        try:
            definition = ScanCreateRequest.model_validate(values)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        with session.no_autoflush:
            await _assign_definition(
                session,
                scan,
                definition,
                retain_unavailable=not replacement
                and body.coverage_mode is None
                and body.campground_ids is None,
            )
    _apply_scan_preference_updates(scan, body)
    await _validate_updated_scan_filters(
        session,
        scan,
        body,
        definition_changed=bool(body.model_fields_set & definition_fields),
    )
    if scan.min_stay_length > (scan.end_date - scan.start_date).days:
        raise HTTPException(status_code=422, detail="Minimum stay exceeds date window")
    scan.definition_revision += 1
    scan.row_version += 1
    scan.current_round_id = None
    scan.round_completed_at = None
    try:
        await reconcile_coverage(session, scan, bump_row_version=False)
        await session.execute(
            update(NotificationOutbox)
            .where(
                NotificationOutbox.scan_id == scan.id,
                NotificationOutbox.status.in_(["pending", "retry"]),
            )
            .values(
                status="skipped",
                finished_at=datetime.datetime.now(datetime.timezone.utc),
                error_category="scan_edited",
            )
        )
        await session.commit()
    except (IntegrityError, StaleDataError) as error:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="scan_changed: Definition changed or already exists"
        ) from error
    return await _scan_to_response(await _load(session, scan_id, current_user.id))


@scan_router.delete("/{scan_id}")
async def delete_scan(
    scan_id: uuid.UUID, current_user: CurrentUserDep, session: SessionDep
) -> Response:
    """Remove only the subscription and its links, preserving shared observations."""
    scan = await _load(session, scan_id, current_user.id)
    await session.delete(scan)
    await session.commit()
    return Response(status_code=204)
