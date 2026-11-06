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
