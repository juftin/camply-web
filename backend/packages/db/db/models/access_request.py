# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

"""
AccessRequest Model — stores early access requests from users.
"""

from __future__ import annotations

import datetime
import uuid
from functools import partial

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class AccessRequest(Base):
    """
    An early access request submitted by a user who hasn't been whitelisted yet.
    """

    __tablename__ = "access_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
