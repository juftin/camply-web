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
    """Scan Wisconsin State Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://wisconsin.goingtocamp.com/api"
    booking_url = "https://wisconsin.goingtocamp.com"
    state_code = "WI"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Wisconsin State Parks."""
        return identities.WisconsinStateParks


class MichiganStateParksProvider(GoingToCampProvider):
    """Scan Michigan State Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://midnrreservations.com/api"
    booking_url = "https://midnrreservations.com"
    state_code = "MI"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Michigan State Parks."""
        return identities.MichiganStateParks


class TacomaPowerParksProvider(GoingToCampProvider):
    """Scan Tacoma Power Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://tacomapower.goingtocamp.com/api"
    booking_url = "https://tacomapower.goingtocamp.com"
    state_code = "WA"
    country_code = "US"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Tacoma Power Parks."""
        return identities.TacomaPowerParks


class ParksCanadaProvider(GoingToCampProvider):
    """Scan Parks Canada via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://reservation.pc.gc.ca/api"
    booking_url = "https://reservation.pc.gc.ca"
    state_code = None
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Parks Canada."""
        return identities.ParksCanada


class BCParksProvider(GoingToCampProvider):
    """Scan BC Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://camping.bcparks.ca/api"
    booking_url = "https://camping.bcparks.ca"
    state_code = "BC"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for BC Parks."""
        return identities.BCParks


class OntarioParksProvider(GoingToCampProvider):
    """Scan Ontario Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://reservations.ontarioparks.ca/api"
    booking_url = "https://reservations.ontarioparks.ca"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Ontario Parks."""
        return identities.OntarioParks


class NovaScotiaParksProvider(GoingToCampProvider):
    """Scan Nova Scotia Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://novascotia.goingtocamp.com/api"
    booking_url = "https://novascotia.goingtocamp.com"
    state_code = "NS"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Nova Scotia Parks."""
        return identities.NovaScotiaParks


class ManitobaParksProvider(GoingToCampProvider):
    """Scan Manitoba Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://manitoba.goingtocamp.com/api"
    booking_url = "https://manitoba.goingtocamp.com"
    state_code = "MB"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Manitoba Parks."""
        return identities.ManitobaParks


class NewfoundlandLabradorParksProvider(GoingToCampProvider):
    """Scan Newfoundland & Labrador Provincial Parks via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://nlcamping.ca/api"
    booking_url = "https://nlcamping.ca"
    state_code = "NL"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Newfoundland & Labrador Provincial Parks."""
        return identities.NewfoundlandLabradorParks


class GatineauParkProvider(GoingToCampProvider):
    """Scan Gatineau Park (NCC) via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://reservations.ncc-ccn.gc.ca/api"
    booking_url = "https://reservations.ncc-ccn.gc.ca"
    state_code = "QC"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Gatineau Park (NCC)."""
        return identities.GatineauPark


class LongPointRegionConservationAuthorityProvider(GoingToCampProvider):
    """Scan Long Point Region Conservation Authority via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://longpoint.goingtocamp.com/api"
    booking_url = "https://longpoint.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Long Point Region Conservation Authority."""
        return identities.LongPointRegionConservationAuthority


class MaitlandValleyConservationAuthorityProvider(GoingToCampProvider):
    """Scan Maitland Valley Conservation Authority via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://maitlandvalley.goingtocamp.com/api"
    booking_url = "https://maitlandvalley.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for Maitland Valley Conservation Authority."""
        return identities.MaitlandValleyConservationAuthority


class StClairRegionConservationAuthorityProvider(GoingToCampProvider):
    """Scan St. Clair Region Conservation Authority via GoingToCamp (seeded disabled until endpoints are verified)."""

    api_url = "https://stclair.goingtocamp.com/api"
    booking_url = "https://stclair.goingtocamp.com"
    state_code = "ON"
    country_code = "CA"

    @property
    def provider(self) -> Provider:
        """Return the permanent database identity for St. Clair Region Conservation Authority."""
        return identities.StClairRegionConservationAuthority
