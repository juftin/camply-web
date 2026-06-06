# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
Scan Result Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.unique_targets import UniqueTarget


class ScanResult(Base):
    """
    Scan Result Model
    """

    __tablename__ = "scan_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unique_targets.id")
    )
    campsite_id: Mapped[str] = mapped_column(String(128))
    available_dates: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    found_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        index=True,
    )

    target: Mapped["UniqueTarget"] = relationship(
        "UniqueTarget",
        back_populates="scan_results",
    )
