"""ReserveCalifornia's current Tyler API and modern booking routes."""

from db.data.providers import ReserveCalifornia
from db.models import Provider
from providers.usedirect.provider import UseDirectProvider


class ReserveCaliforniaProvider(UseDirectProvider):
    """Scan California state parks through the current public UseDirect API."""

    api_url = (
        "https://california-rdr.prod.cali.rd12.recreation-management.tylerapp.com/rdr"
    )
    booking_url = "https://www.reservecalifornia.com"
    state_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return California's permanent database identity."""
        return ReserveCalifornia

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """Open a state park in the modern reservation application."""
        return f"{cls.booking_url}/park/{rec_area_id}"

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """Open a campground when park context is supplied; otherwise open search."""
        if rec_area_id is None:
            return cls.booking_url
        return f"{cls.booking_url}/park/{rec_area_id}/{campground_id}"
