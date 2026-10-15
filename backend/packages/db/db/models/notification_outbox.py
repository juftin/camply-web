"""Durable standalone delivery intents committed alongside availability results."""

import datetime
import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base


class NotificationOutbox(Base):
    """Retain pending alerts across application restarts without broker services."""

    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("detection_id", "scan_id", "campsite_id"),
        CheckConstraint("attempt_count >= 0 AND attempt_count <= 4"),
        CheckConstraint(
            "status IN ('pending', 'sending', 'retry', 'sent', 'skipped', 'failed')"
        ),
        CheckConstraint(
            "status NOT IN ('sent', 'skipped', 'failed') OR finished_at IS NOT NULL"
        ),
        Index("ix_notification_outbox_due", "status", "next_attempt_at"),
        Index("ix_notification_outbox_finished", "finished_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    """Stable delivery identity, reused by every attempt."""
    detection_id: Mapped[uuid.UUID] = mapped_column()
    """Identity of the successful scan transaction that detected this opening."""
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    """Current recipient; deletion makes pending delivery ineligible."""
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_scans.id", ondelete="SET NULL")
    )
    """Subscription whose current filters must still match."""
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("unique_targets.id", ondelete="SET NULL")
    )
    """Original target, so relinked scans cannot receive stale alerts."""
    campsite_id: Mapped[str] = mapped_column(String(128))
    """Provider campsite identity scoped to this target."""
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    """Credential-free serialized NotificationDTO."""
    status: Mapped[str] = mapped_column(String(16), default="pending")
    """Delivery lifecycle state."""
    attempt_count: Mapped[int] = mapped_column(default=0)
    """Consumed attempts, including interrupted sends."""
    next_attempt_at: Mapped[datetime.datetime] = mapped_column()
    """UTC time at which the consumer may attempt delivery."""
    created_at: Mapped[datetime.datetime] = mapped_column()
    """UTC detection time."""
    finished_at: Mapped[datetime.datetime | None] = mapped_column()
    """UTC terminal outcome time; absent while pending."""
    error_category: Mapped[str | None] = mapped_column(String(64))
    """Allowlisted outcome category, never a raw exception."""
