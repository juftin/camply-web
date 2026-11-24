"""Verified GoingToCamp deployments with their API and booking roots.

Deployment attributes are documented on GoingToCampProvider.
"""

from camply.db.data import providers as identities
from camply.db.models import Provider
from camply.providers.going_to_camp.provider import GoingToCampProvider


class WashingtonStateParksProvider(GoingToCampProvider):
    """Scan Washington State Parks campgrounds and lodging via GoingToCamp."""

    api_url = "https://washington.goingtocamp.com/api"
    booking_url = "https://washington.goingtocamp.com"
    state_code = "WA"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return Washington State Parks' permanent database identity."""
        return identities.WashingtonStateParks


class WisconsinStateParksProvider(GoingToCampProvider):
    """Scan Wisconsin State Parks campgrounds and lodging via GoingToCamp."""

    api_url = "https://wisconsin.goingtocamp.com/api"
    booking_url = "https://wisconsin.goingtocamp.com"
    state_code = "WI"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return Wisconsin State Parks' permanent database identity."""
        return identities.WisconsinStateParks


class MichiganStateParksProvider(GoingToCampProvider):
    """Scan Michigan State Parks campgrounds and lodging via GoingToCamp."""

    api_url = "https://midnrreservations.com/api"
    booking_url = "https://midnrreservations.com"
    state_code = "MI"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return Michigan State Parks' permanent database identity."""
        return identities.MichiganStateParks


class TacomaPowerParksProvider(GoingToCampProvider):
    """Scan Tacoma Power Parks campgrounds via GoingToCamp."""

    api_url = "https://tacomapower.goingtocamp.com/api"
    booking_url = "https://tacomapower.goingtocamp.com"
    state_code = "WA"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return Tacoma Power Parks' permanent database identity."""
        return identities.TacomaPowerParks


class ParksCanadaProvider(GoingToCampProvider):
    """Scan Parks Canada campgrounds and backcountry sites via GoingToCamp."""

    api_url = "https://reservation.pc.gc.ca/api"
    booking_url = "https://reservation.pc.gc.ca"
    state_code = None
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Parks Canada's permanent database identity."""
        return identities.ParksCanada


class BCParksProvider(GoingToCampProvider):
    """Scan BC Parks campgrounds via GoingToCamp."""

    api_url = "https://camping.bcparks.ca/api"
    booking_url = "https://camping.bcparks.ca"
    state_code = "BC"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return BC Parks' permanent database identity."""
        return identities.BCParks


class OntarioParksProvider(GoingToCampProvider):
    """Scan Ontario Parks campgrounds and roofed accommodations via GoingToCamp."""

    api_url = "https://reservations.ontarioparks.ca/api"
    booking_url = "https://reservations.ontarioparks.ca"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Ontario Parks' permanent database identity."""
        return identities.OntarioParks


class NovaScotiaParksProvider(GoingToCampProvider):
    """Scan Nova Scotia Parks campgrounds via GoingToCamp."""

    api_url = "https://novascotia.goingtocamp.com/api"
    booking_url = "https://novascotia.goingtocamp.com"
    state_code = "NS"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Nova Scotia Parks' permanent database identity."""
        return identities.NovaScotiaParks


class ManitobaParksProvider(GoingToCampProvider):
    """Scan Manitoba Parks campgrounds via GoingToCamp."""

    api_url = "https://manitoba.goingtocamp.com/api"
    booking_url = "https://manitoba.goingtocamp.com"
    state_code = "MB"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Manitoba Parks' permanent database identity."""
        return identities.ManitobaParks


class NewfoundlandAndLabradorParksProvider(GoingToCampProvider):
    """Scan Newfoundland & Labrador Provincial Parks via GoingToCamp."""

    api_url = "https://www.nlcamping.ca/api"
    booking_url = "https://www.nlcamping.ca"
    state_code = "NL"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Newfoundland & Labrador Provincial Parks' permanent database identity."""
        return identities.NewfoundlandAndLabradorParks


class GatineauParkProvider(GoingToCampProvider):
    """Scan NCC Gatineau Park campgrounds via GoingToCamp."""

    api_url = "https://reservations.ncc-ccn.gc.ca/api"
    booking_url = "https://reservations.ncc-ccn.gc.ca"
    state_code = "QC"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Gatineau Park's permanent database identity."""
        return identities.GatineauPark


class LongPointRegionProvider(GoingToCampProvider):
    """Scan Long Point Region Conservation Authority campgrounds via GoingToCamp."""

    api_url = "https://longpoint.goingtocamp.com/api"
    booking_url = "https://longpoint.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Long Point Region's permanent database identity."""
        return identities.LongPointRegion


class MaitlandValleyProvider(GoingToCampProvider):
    """Scan Maitland Valley Conservation Authority campgrounds via GoingToCamp."""

    api_url = "https://maitlandvalley.goingtocamp.com/api"
    booking_url = "https://maitlandvalley.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return Maitland Valley's permanent database identity."""
        return identities.MaitlandValley


class StClairRegionProvider(GoingToCampProvider):
    """Scan St. Clair Region Conservation Authority campgrounds via GoingToCamp."""

    api_url = "https://stclair.goingtocamp.com/api"
    booking_url = "https://stclair.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return St. Clair Region's permanent database identity."""
        return identities.StClairRegion
