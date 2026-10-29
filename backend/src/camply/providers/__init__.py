"""
Providers
"""

from camply.db.data import providers as identities
from camply.providers.base import BaseProvider
from camply.providers.recreation_gov.provider import RecreationGovProvider
from camply.providers.usedirect.variations import (
    ArizonaStateParksProvider,
    FairfaxCountyParksProvider,
    FloridaStateParksProvider,
    MinnesotaStateParksProvider,
    MissouriStateParksProvider,
    NorthernTerritoryProvider,
    OhioStateParksProvider,
    OregonMetroProvider,
    ReserveCaliforniaProvider,
    VirginiaStateParksProvider,
)

PROVIDERS: dict[int, type[BaseProvider]] = {
    identities.RecreationDotGov.id: RecreationGovProvider,
    identities.ReserveCalifornia.id: ReserveCaliforniaProvider,
    identities.FloridaStateParks.id: FloridaStateParksProvider,
    identities.VirginiaStateParks.id: VirginiaStateParksProvider,
    identities.MinnesotaStateParks.id: MinnesotaStateParksProvider,
    identities.OhioStateParks.id: OhioStateParksProvider,
    identities.ArizonaStateParks.id: ArizonaStateParksProvider,
    identities.MissouriStateParks.id: MissouriStateParksProvider,
    identities.FairfaxCountyParks.id: FairfaxCountyParksProvider,
    identities.OregonMetro.id: OregonMetroProvider,
    identities.NorthernTerritory.id: NorthernTerritoryProvider,
}

__all__ = ["PROVIDERS"]
