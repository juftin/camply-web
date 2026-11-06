"""
Providers
"""

from camply.db.data import providers as identities
from camply.db.models.providers import Provider
from camply.providers.base import BaseProvider
from camply.providers.going_to_camp.variations import (
    BCParksProvider,
    GatineauParkProvider,
    LongPointRegionConservationAuthorityProvider,
    MaitlandValleyConservationAuthorityProvider,
    ManitobaParksProvider,
    MichiganStateParksProvider,
    NewfoundlandLabradorParksProvider,
    NovaScotiaParksProvider,
    OntarioParksProvider,
    ParksCanadaProvider,
    StClairRegionConservationAuthorityProvider,
    TacomaPowerParksProvider,
    WashingtonStateParksProvider,
    WisconsinStateParksProvider,
)
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
    identities.WashingtonStateParks.id: WashingtonStateParksProvider,
    identities.WisconsinStateParks.id: WisconsinStateParksProvider,
    identities.MichiganStateParks.id: MichiganStateParksProvider,
    identities.TacomaPowerParks.id: TacomaPowerParksProvider,
    identities.ParksCanada.id: ParksCanadaProvider,
    identities.BCParks.id: BCParksProvider,
    identities.OntarioParks.id: OntarioParksProvider,
    identities.NovaScotiaParks.id: NovaScotiaParksProvider,
    identities.ManitobaParks.id: ManitobaParksProvider,
    identities.NewfoundlandLabradorParks.id: NewfoundlandLabradorParksProvider,
    identities.GatineauPark.id: GatineauParkProvider,
    identities.LongPointRegionConservationAuthority.id: LongPointRegionConservationAuthorityProvider,
    identities.MaitlandValleyConservationAuthority.id: MaitlandValleyConservationAuthorityProvider,
    identities.StClairRegionConservationAuthority.id: StClairRegionConservationAuthorityProvider,
}

_DISABLED_PROVIDER_IDS = frozenset(
    identity.id
    for identity in vars(identities).values()
    if isinstance(identity, Provider) and not identity.enabled
)

# Registered providers whose identity is enabled. Scheduled and bulk catalog syncs
# use this view so unverified deployments are not polled. Disabled providers stay
# in ``PROVIDERS`` and can still be run explicitly, for example
# ``camply db metadata --provider-id 13`` while verifying them.
CATALOG_PROVIDERS: dict[int, type[BaseProvider]] = {
    provider_id: provider_cls
    for provider_id, provider_cls in PROVIDERS.items()
    if provider_id not in _DISABLED_PROVIDER_IDS
}

__all__ = ["CATALOG_PROVIDERS", "PROVIDERS"]
