"""
User Scan Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING, Literal

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    event,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from camply.db.models.base import Base

if TYPE_CHECKING:
    from camply.db.models.scan_targets import ScanTarget
    from camply.db.models.unique_targets import UniqueTarget
    from camply.db.models.users import User


class UserScan(Base):
    """
    User Scan Model
    """

    __tablename__ = "user_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unique_targets.id")
    )
    destination_type: Mapped[Literal["campground", "recreation_area"]] = mapped_column(
        String(24), default="campground", server_default="campground"
    )
    """Saved destination kind; an area never has a synthetic campground target."""
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    campground_id: Mapped[str | None] = mapped_column(String(128))
    recreation_area_id: Mapped[str | None] = mapped_column(String(128))
    destination_name: Mapped[str] = mapped_column(String(255), default="")
    coverage_mode: Mapped[Literal["all", "selected"] | None] = mapped_column(String(16))
    selected_campgrounds: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list
    )
    start_date: Mapped[datetime.date] = mapped_column(Date)
    end_date: Mapped[datetime.date] = mapped_column(Date)
    definition_hash: Mapped[str] = mapped_column(String(64))
    definition_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    coverage_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    row_version: Mapped[int] = mapped_column(default=1, server_default="1")
    current_round_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    round_started_at: Mapped[datetime.datetime | None] = mapped_column()
    round_deadline_at: Mapped[datetime.datetime | None] = mapped_column()
    round_completed_at: Mapped[datetime.datetime | None] = mapped_column()
    last_full_checked_at: Mapped[datetime.datetime | None] = mapped_column()

    __table_args__ = (
        UniqueConstraint("user_id", "definition_hash", name="uq_user_scan_definition"),
        CheckConstraint("end_date > start_date", name="ck_scan_dates"),
        CheckConstraint(
            "definition_revision > 0 AND coverage_revision > 0 AND row_version > 0",
            name="ck_scan_versions",
        ),
        CheckConstraint(
            "(destination_type = 'campground' AND campground_id IS NOT NULL AND target_id IS NOT NULL AND recreation_area_id IS NULL AND coverage_mode IS NULL) OR (destination_type = 'recreation_area' AND recreation_area_id IS NOT NULL AND campground_id IS NULL AND target_id IS NULL AND coverage_mode IN ('all', 'selected'))",
            name="ck_scan_destination",
        ),
    )
    __mapper_args__ = {"version_id_col": row_version, "version_id_generator": False}

    coverage: Mapped[list["ScanTarget"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan", lazy="selectin"
    )
    """Resolved shared targets; removing links never removes their observations."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stay_length: Mapped[int] = mapped_column(Integer, default=1)
    preferred_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String).with_variant(JSON(), "sqlite")
    )
    require_electric: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_scans",
    )
    target: Mapped["UniqueTarget"] = relationship(
        "UniqueTarget",
        back_populates="user_scans",
    )


@event.listens_for(UserScan, "before_insert")
def populate_legacy_definition(
    mapper: Mapper[UserScan], connection: Connection, scan: UserScan
) -> None:
    """Support existing campground writers while persisting a complete definition."""
    from camply.db.coverage import definition_hash
    from camply.db.models.campgrounds import Campground
    from camply.db.models.unique_targets import UniqueTarget

    if scan.target_id and scan.provider_id is None:
        target = (
            connection.execute(
                select(UniqueTarget.__table__).where(UniqueTarget.id == scan.target_id)
            )
            .mappings()
            .one()
        )
        scan.provider_id = target["provider_id"]
        scan.campground_id = target["campground_id"]
        scan.start_date = target["start_date"]
        scan.end_date = target["end_date"]
        scan.destination_name = (
            connection.scalar(
                select(Campground.name).where(
                    Campground.provider_id == scan.provider_id,
                    Campground.id == scan.campground_id,
                )
            )
            or scan.campground_id
        )
    if not scan.definition_hash:
        scan.definition_hash = definition_hash(
            provider_id=scan.provider_id,
            destination_type=scan.destination_type or "campground",
            destination_id=scan.recreation_area_id or scan.campground_id or "",
            start_date=scan.start_date,
            end_date=scan.end_date,
            coverage_mode=scan.coverage_mode,
            selected_ids=[item["id"] for item in scan.selected_campgrounds or []],
        )


@event.listens_for(UserScan, "after_insert")
def link_legacy_target(
    mapper: Mapper[UserScan], connection: Connection, scan: UserScan
) -> None:
    """Keep compatibility writers on the same association used by area scans."""
    from camply.db.models.scan_targets import ScanTarget

    if scan.target_id:
        connection.execute(
            insert(ScanTarget).values(
                scan_id=scan.id,
                target_id=scan.target_id,
                coverage_revision=scan.coverage_revision or 1,
                outcome="pending",
            )
        )
