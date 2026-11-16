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
WisconsinStateParks, MichiganStateParks, TacomaPowerParks : Provider
    Stable identities for US GoingToCamp deployments.
ParksCanada, BCParks, OntarioParks, NovaScotiaParks, ManitobaParks : Provider
    Stable identities for Canadian federal and provincial GoingToCamp deployments.
NewfoundlandAndLabradorParks, GatineauPark : Provider
    Stable identities for Newfoundland & Labrador and Gatineau Park on GoingToCamp.
LongPointRegion, MaitlandValley, StClairRegion : Provider
    Stable identities for Ontario conservation authority GoingToCamp deployments.
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

ReserveAmerica = Provider(
    id=13,
    name="ReserveAmerica",
    description="ReserveAmerica native overnight campsite reservations.",
    url="https://www.reserveamerica.com",
    enabled=True,
)

WisconsinStateParks = Provider(
    id=14,
    name="Wisconsin State Parks",
    description="Wisconsin State Parks campsite reservations.",
    url="https://wisconsin.goingtocamp.com",
    enabled=True,
)

MichiganStateParks = Provider(
    id=15,
    name="Michigan State Parks",
    description="Michigan Department of Natural Resources campsite reservations.",
    url="https://midnrreservations.com",
    enabled=True,
)

TacomaPowerParks = Provider(
    id=16,
    name="Tacoma Power Parks",
    description="Tacoma Power Parks campsite reservations.",
    url="https://tacomapower.goingtocamp.com",
    enabled=True,
)

ParksCanada = Provider(
    id=17,
    name="Parks Canada",
    description="Parks Canada campsite and backcountry reservations.",
    url="https://reservation.pc.gc.ca",
    enabled=True,
)

BCParks = Provider(
    id=18,
    name="BC Parks",
    description="British Columbia provincial parks campsite reservations.",
    url="https://camping.bcparks.ca",
    enabled=True,
)

OntarioParks = Provider(
    id=19,
    name="Ontario Parks",
    description="Ontario provincial parks campsite reservations.",
    url="https://reservations.ontarioparks.ca",
    enabled=True,
)

NovaScotiaParks = Provider(
    id=20,
    name="Nova Scotia Parks",
    description="Nova Scotia provincial parks campsite reservations.",
    url="https://novascotia.goingtocamp.com",
    enabled=True,
)

ManitobaParks = Provider(
    id=21,
    name="Manitoba Parks",
    description="Manitoba provincial parks campsite reservations.",
    url="https://manitoba.goingtocamp.com",
    enabled=True,
)

NewfoundlandAndLabradorParks = Provider(
    id=22,
    name="Newfoundland & Labrador Provincial Parks",
    description="Newfoundland & Labrador provincial parks campsite reservations.",
    url="https://www.nlcamping.ca",
    enabled=True,
)

GatineauPark = Provider(
    id=23,
    name="Gatineau Park",
    description="National Capital Commission Gatineau Park campsite reservations.",
    url="https://reservations.ncc-ccn.gc.ca",
    enabled=True,
)

LongPointRegion = Provider(
    id=24,
    name="Long Point Region",
    description="Long Point Region Conservation Authority campsite reservations.",
    url="https://longpoint.goingtocamp.com",
    enabled=True,
)

MaitlandValley = Provider(
    id=25,
    name="Maitland Valley",
    description="Maitland Valley Conservation Authority campsite reservations.",
    url="https://maitlandvalley.goingtocamp.com",
    enabled=True,
)

StClairRegion = Provider(
    id=26,
    name="St. Clair Region",
    description="St. Clair Region Conservation Authority campsite reservations.",
    url="https://stclair.goingtocamp.com",
    enabled=True,
)
