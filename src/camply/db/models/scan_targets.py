"""Resolved scan coverage and durable current-round member outcomes."""

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from camply.db.models.base import Base

if TYPE_CHECKING:
    from camply.db.models.unique_targets import UniqueTarget
    from camply.db.models.user_scans import UserScan


class ScanTarget(Base):
    """Link a subscription to shared observations without owning those observations."""

    __tablename__ = "scan_targets"
    __table_args__ = (
        CheckConstraint("coverage_revision > 0", name="ck_scan_target_revision"),
        CheckConstraint(
            "outcome IN ('pending', 'retrying', 'success', 'failed')",
            name="ck_scan_target_outcome",
        ),
        Index("ix_scan_targets_target", "target_id"),
        Index("ix_scan_targets_round", "scan_id", "round_id", "outcome"),
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_scans.id", ondelete="CASCADE"), primary_key=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("unique_targets.id"), primary_key=True
    )
    coverage_revision: Mapped[int] = mapped_column(default=1, server_default="1")
    round_id: Mapped[uuid.UUID | None] = mapped_column()
    outcome: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column()
    successful_at: Mapped[datetime.datetime | None] = mapped_column()
    failed_at: Mapped[datetime.datetime | None] = mapped_column()
    error_category: Mapped[str | None] = mapped_column(String(64))
    scan: Mapped["UserScan"] = relationship(back_populates="coverage")
    target: Mapped["UniqueTarget"] = relationship(lazy="selectin")
