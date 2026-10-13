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
"""

from db.models.providers import Provider
from db.utils import format_description

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
