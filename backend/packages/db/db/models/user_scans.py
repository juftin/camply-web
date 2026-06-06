# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
User Scan Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, JSON, Boolean, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.unique_targets import UniqueTarget
    from db.models.users import User


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
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unique_targets.id")
    )
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
