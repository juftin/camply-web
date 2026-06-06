# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Unique Target Model
"""

import datetime
import hashlib
import uuid
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.campgrounds import Campground
    from db.models.providers import Provider
    from db.models.scan_results import ScanResult
    from db.models.user_scans import UserScan


class UniqueTarget(Base):
    """
    Unique Target Model
    """

    __tablename__ = "unique_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("providers.id"))
    campground_id: Mapped[str] = mapped_column(String(128))
    start_date: Mapped[datetime.date] = mapped_column(Date)
    end_date: Mapped[datetime.date] = mapped_column(Date)
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    last_checked_at: Mapped[datetime.datetime | None] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["campground_id", "provider_id"],
            ["campgrounds.id", "campgrounds.provider_id"],
        ),
    )

    provider: Mapped["Provider"] = relationship(
        "Provider",
        foreign_keys=[provider_id],
    )
    campground: Mapped["Campground"] = relationship(
        "Campground",
        foreign_keys=[campground_id, provider_id],
        overlaps="provider",
    )
    user_scans: Mapped[list["UserScan"]] = relationship(
        back_populates="target",
    )
    scan_results: Mapped[list["ScanResult"]] = relationship(
        back_populates="target",
    )

    @staticmethod
    def calculate_hash(
        provider_id: int,
        campground_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> str:
        """
        Calculate hash for de-duplication
        """
        hash_input = f"{provider_id}:{campground_id}:{start_date.isoformat()}:{end_date.isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()


@event.listens_for(UniqueTarget, "before_insert")
def receive_before_insert(mapper, connection, target: UniqueTarget):
    """
    Automatically calculate hash before insert
    """
    if not target.hash:
        target.hash = UniqueTarget.calculate_hash(
            target.provider_id, target.campground_id, target.start_date, target.end_date
        )
