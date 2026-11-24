"""
RecreationArea
"""

import datetime
from functools import partial
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from camply.db.models.base import Base

if TYPE_CHECKING:
    from camply.db.models.campgrounds import Campground
    from camply.db.models.providers import Provider


class RecreationArea(Base):
    """
    Recreation Area Model
    """

    __tablename__ = "recreation_areas"

    id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    provider_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("providers.id"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(String(32768))
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )
    """Last successful provider enrichment; never inherited by child campgrounds."""
    details_attempted_at: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True
    )
    """Last refresh attempt; separate from successful content provenance."""
    city: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(50))
    longitude: Mapped[float | None] = mapped_column()
    latitude: Mapped[float | None] = mapped_column()
    reservable: Mapped[bool] = mapped_column(default=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=partial(datetime.datetime.now, tz=datetime.timezone.utc),
        server_default=func.CURRENT_TIMESTAMP(),
        onupdate=func.CURRENT_TIMESTAMP(),
    )

    provider: Mapped["Provider"] = relationship(
        back_populates="recreation_areas",
    )
    campgrounds: Mapped[list["Campground"]] = relationship(
        foreign_keys="[Campground.recreation_area_id, Campground.provider_id]",
        viewonly=True,
    )
