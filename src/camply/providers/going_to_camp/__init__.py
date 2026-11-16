"""GoingToCamp / Camis async reservation providers."""

from camply.providers.going_to_camp.provider import GoingToCampProvider
from camply.providers.going_to_camp.variations import (
    BCParksProvider,
    GatineauParkProvider,
    LongPointRegionProvider,
    MaitlandValleyProvider,
    ManitobaParksProvider,
    MichiganStateParksProvider,
    NewfoundlandAndLabradorParksProvider,
    NovaScotiaParksProvider,
    OntarioParksProvider,
    ParksCanadaProvider,
    StClairRegionProvider,
    TacomaPowerParksProvider,
    WashingtonStateParksProvider,
    WisconsinStateParksProvider,
)

__all__ = [
    "BCParksProvider",
    "GatineauParkProvider",
    "GoingToCampProvider",
    "LongPointRegionProvider",
    "MaitlandValleyProvider",
    "ManitobaParksProvider",
    "MichiganStateParksProvider",
    "NewfoundlandAndLabradorParksProvider",
    "NovaScotiaParksProvider",
    "OntarioParksProvider",
    "ParksCanadaProvider",
    "StClairRegionProvider",
    "TacomaPowerParksProvider",
    "WashingtonStateParksProvider",
    "WisconsinStateParksProvider",
]
