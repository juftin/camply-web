"""Verified UseDirect deployments with their API and booking variations.

Deployment attributes are documented on UseDirectProvider.
"""

from camply.db.data import providers as identities
from camply.db.models import Provider
from camply.providers.usedirect.provider import UseDirectProvider


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
        return identities.ReserveCalifornia

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


class FloridaStateParksProvider(UseDirectProvider):
    """Scan Florida State Parks through its public RDR deployment."""

    api_url = "https://floridardr.usedirect.com/FloridaRDR/rdr"
    booking_url = "https://reserve.floridastateparks.org/Web"
    state_code = "FL"

    @property
    def provider(self) -> Provider:
        """Return Florida's permanent database identity."""
        return identities.FloridaStateParks


class VirginiaStateParksProvider(UseDirectProvider):
    """Scan Virginia State Parks through its current Tyler deployment."""

    api_url = "https://prod-va-rdr.recreation-management.tylerapp.com/virginiardr/rdr"
    booking_url = "https://reservevaparks.com/Web"
    state_code = "VA"

    @property
    def provider(self) -> Provider:
        """Return Virginia's permanent database identity."""
        return identities.VirginiaStateParks


class MinnesotaStateParksProvider(UseDirectProvider):
    """Scan Minnesota State Parks through its public RDR deployment."""

    api_url = "https://mnrdr.usedirect.com/minnesotardr/rdr"
    booking_url = "https://reservemn.usedirect.com/MinnesotaWeb"
    state_code = "MN"

    @property
    def provider(self) -> Provider:
        """Return Minnesota's permanent database identity."""
        return identities.MinnesotaStateParks


class OhioStateParksProvider(UseDirectProvider):
    """Scan Ohio State Parks and link to its current reservation host."""

    api_url = "https://ohiordr.usedirect.com/ohiordr/rdr"
    booking_url = "https://reserveohio.com/OhioCampWeb"
    state_code = "OH"

    @property
    def provider(self) -> Provider:
        """Return Ohio's permanent database identity."""
        return identities.OhioStateParks


class ArizonaStateParksProvider(UseDirectProvider):
    """Scan Arizona State Parks through its public RDR deployment."""

    api_url = "https://azrdr.usedirect.com/azrdr/rdr"
    booking_url = "https://azstateparks.com/reserve"
    state_code = "AZ"

    @property
    def provider(self) -> Provider:
        """Return Arizona's permanent database identity."""
        return identities.ArizonaStateParks


class MissouriStateParksProvider(UseDirectProvider):
    """Scan Missouri State Parks and link to its current reservation host."""

    api_url = "https://msprdr.usedirect.com/msprdr/rdr"
    booking_url = "https://icampmo.usedirect.com/MSPWeb"
    state_code = "MO"

    @property
    def provider(self) -> Provider:
        """Return Missouri's permanent database identity."""
        return identities.MissouriStateParks


class FairfaxCountyParksProvider(UseDirectProvider):
    """Scan Fairfax County Parks and open its reservation search application."""

    api_url = "https://fairfaxrdr.usedirect.com/FCPARDR/rdr"
    booking_url = "https://fairfax.usedirect.com/FairfaxFCPAWeb"
    state_code = "VA"
    booking_path_params = False

    @property
    def provider(self) -> Provider:
        """Return Fairfax County's permanent database identity."""
        return identities.FairfaxCountyParks


class OregonMetroProvider(UseDirectProvider):
    """Scan Oregon Metro and open its reservation search application."""

    api_url = "https://oregonrdr.usedirect.com/oregonmetrordr/rdr"
    booking_url = "https://reservemetro.usedirect.com/MetroWeb"
    state_code = "OR"
    booking_path_params = False

    @property
    def provider(self) -> Provider:
        """Return Oregon Metro's permanent database identity."""
        return identities.OregonMetro


class NorthernTerritoryProvider(UseDirectProvider):
    """Scan Australian Northern Territory parks with Australian locations."""

    api_url = "https://northernterritoryrdr.usedirect.com/NorthernTerritoryRDR/rdr"
    booking_url = "https://parkbookings.nt.gov.au/Web"
    state_code = "NT"
    country_code = "AU"
    booking_path_params = False

    @property
    def provider(self) -> Provider:
        """Return Northern Territory's permanent database identity."""
        return identities.NorthernTerritory
