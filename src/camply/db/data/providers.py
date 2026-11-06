"""
Providers Seed Data

Attributes
----------
ReserveCalifornia : Provider
    Stable provider identity for California state park inventory.
FloridaStateParks, VirginiaStateParks, MinnesotaStateParks : Provider
    Stable identities for Florida, Virginia, and Minnesota state parks.
OhioStateParks, ArizonaStateParks, MissouriStateParks : Provider
    Stable identities for Ohio, Arizona, and Missouri state parks.
FairfaxCountyParks, OregonMetro, NorthernTerritory : Provider
    Stable identities for regional parks and Australia's Northern Territory.
WashingtonStateParks : Provider
    Stable identity for Washington State Parks on GoingToCamp.
WisconsinStateParks, MichiganStateParks, TacomaPowerParks, ParksCanada, BCParks, OntarioParks, NovaScotiaParks, ManitobaParks, NewfoundlandLabradorParks, GatineauPark, LongPointRegionConservationAuthority, MaitlandValleyConservationAuthority, StClairRegionConservationAuthority : Provider
    Stable identities (IDs 13-25) for additional GoingToCamp deployments, seeded
    disabled until their public endpoints are verified.
"""

from camply.db.models.providers import Provider
from camply.db.utils import format_description

RecreationDotGov = Provider(
    id=1,
    name="Recreation.gov",
    description=format_description("""
        Recreation.gov is the government's centralized travel planning platform and
        reservation system for 14 federal agencies, offering the tools, tips, and
        information needed for you to discover destinations and activities, plan
        a trip, and explore outdoor and cultural destinations in your zip code
        and across the country. Find and reserve incredible experiences that
        help you bring home a story through Recreation.gov!
    """),
    url="https://www.recreation.gov",
    enabled=True,
)

ReserveCalifornia = Provider(
    id=2,
    name="ReserveCalifornia",
    description="California State Parks campsite reservations.",
    url="https://www.reservecalifornia.com",
    enabled=True,
)

FloridaStateParks = Provider(
    id=3,
    name="Florida State Parks",
    description="Florida State Parks campsite reservations.",
    url="https://reserve.floridastateparks.org/Web",
    enabled=True,
)

VirginiaStateParks = Provider(
    id=4,
    name="Virginia State Parks",
    description="Virginia State Parks campsite reservations.",
    url="https://reservevaparks.com/Web",
    enabled=True,
)

MinnesotaStateParks = Provider(
    id=5,
    name="Minnesota State Parks",
    description="Minnesota State Parks campsite reservations.",
    url="https://reservemn.usedirect.com/MinnesotaWeb",
    enabled=True,
)

OhioStateParks = Provider(
    id=6,
    name="Ohio State Parks",
    description="Ohio State Parks campsite reservations.",
    url="https://reserveohio.com/OhioCampWeb",
    enabled=True,
)

ArizonaStateParks = Provider(
    id=7,
    name="Arizona State Parks",
    description="Arizona State Parks campsite reservations.",
    url="https://azstateparks.com/reserve",
    enabled=True,
)

MissouriStateParks = Provider(
    id=8,
    name="Missouri State Parks",
    description="Missouri State Parks campsite reservations.",
    url="https://icampmo.usedirect.com/MSPWeb",
    enabled=True,
)

FairfaxCountyParks = Provider(
    id=9,
    name="Fairfax County Parks",
    description="Fairfax County Parks campsite reservations.",
    url="https://fairfax.usedirect.com/FairfaxFCPAWeb",
    enabled=True,
)

OregonMetro = Provider(
    id=10,
    name="Oregon Metro",
    description="Oregon Metro regional park campsite reservations.",
    url="https://reservemetro.usedirect.com/MetroWeb",
    enabled=True,
)

NorthernTerritory = Provider(
    id=11,
    name="Northern Territory",
    description="Australian Northern Territory park campsite reservations.",
    url="https://parkbookings.nt.gov.au/Web",
    enabled=True,
)

WashingtonStateParks = Provider(
    id=12,
    name="Washington State Parks",
    description="Washington State Parks campsite reservations.",
    url="https://washington.goingtocamp.com",
    enabled=True,
)

WisconsinStateParks = Provider(
    id=13,
    name="Wisconsin State Parks",
    description="Wisconsin State Parks campsite reservations.",
    url="https://wisconsin.goingtocamp.com",
    enabled=False,
)

MichiganStateParks = Provider(
    id=14,
    name="Michigan State Parks",
    description="Michigan Department of Natural Resources campsite reservations.",
    url="https://midnrreservations.com",
    enabled=False,
)

TacomaPowerParks = Provider(
    id=15,
    name="Tacoma Power Parks",
    description="Tacoma Power Parks campsite reservations.",
    url="https://tacomapower.goingtocamp.com",
    enabled=False,
)

ParksCanada = Provider(
    id=16,
    name="Parks Canada",
    description="Parks Canada campsite reservations.",
    url="https://reservation.pc.gc.ca",
    enabled=False,
)

BCParks = Provider(
    id=17,
    name="BC Parks",
    description="BC Parks campsite reservations.",
    url="https://camping.bcparks.ca",
    enabled=False,
)

OntarioParks = Provider(
    id=18,
    name="Ontario Parks",
    description="Ontario Parks campsite reservations.",
    url="https://reservations.ontarioparks.ca",
    enabled=False,
)

NovaScotiaParks = Provider(
    id=19,
    name="Nova Scotia Parks",
    description="Nova Scotia Provincial Parks campsite reservations.",
    url="https://novascotia.goingtocamp.com",
    enabled=False,
)

ManitobaParks = Provider(
    id=20,
    name="Manitoba Parks",
    description="Manitoba Provincial Parks campsite reservations.",
    url="https://manitoba.goingtocamp.com",
    enabled=False,
)

NewfoundlandLabradorParks = Provider(
    id=21,
    name="Newfoundland & Labrador Provincial Parks",
    description="Newfoundland and Labrador Provincial Parks campsite reservations.",
    url="https://nlcamping.ca",
    enabled=False,
)

GatineauPark = Provider(
    id=22,
    name="Gatineau Park (NCC)",
    description="National Capital Commission Gatineau Park campsite reservations.",
    url="https://reservations.ncc-ccn.gc.ca",
    enabled=False,
)

LongPointRegionConservationAuthority = Provider(
    id=23,
    name="Long Point Region Conservation Authority",
    description="Long Point Region Conservation Authority campsite reservations.",
    url="https://longpoint.goingtocamp.com",
    enabled=False,
)

MaitlandValleyConservationAuthority = Provider(
    id=24,
    name="Maitland Valley Conservation Authority",
    description="Maitland Valley Conservation Authority campsite reservations.",
    url="https://maitlandvalley.goingtocamp.com",
    enabled=False,
)

StClairRegionConservationAuthority = Provider(
    id=25,
    name="St. Clair Region Conservation Authority",
    description="St. Clair Region Conservation Authority campsite reservations.",
    url="https://stclair.goingtocamp.com",
    enabled=False,
)
