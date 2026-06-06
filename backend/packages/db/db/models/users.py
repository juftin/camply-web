# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
User Model
"""

import datetime
import uuid
from functools import partial
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base

if TYPE_CHECKING:
    from db.models.user_scans import UserScan


class User(Base):
    """
    User Model
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auth0_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_early_access_user: Mapped[bool] = mapped_column(Boolean, default=False)
    pushover_token: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
    )

    user_scans: Mapped[list["UserScan"]] = relationship(
        back_populates="user",
    )
