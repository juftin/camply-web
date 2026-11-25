"""Recorded metadata targets and independently verified provider identities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetadataTarget:
    """A public campground and its supported parent relationship."""

    family: str
    provider_id: int
    query: str
    campground_id: str
    campground_name: str
    state: str
    country: str
    booking_url: str
    area_id: str | None = None
    area_name: str | None = None
    siblings: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Stable family name used for fixture paths and parameter IDs."""
        return self.family


TARGETS = (
    MetadataTarget(
        family="recreation-gov",
        provider_id=1,
        query="Jumbo Rocks",
        campground_id="272300",
        campground_name="JUMBO ROCKS CAMPGROUND",
        state="CA",
        country="US",
        booking_url="https://www.recreation.gov/camping/campgrounds/272300",
        area_id="2782",
        area_name="Joshua Tree National Park",
        siblings=(
            "232473",
            "234723",
            "272299",
            "232471",
            "232472",
            "10053779",
            "272300",
            "10056207",
            "232470",
        ),
    ),
    MetadataTarget(
        family="usedirect",
        provider_id=2,
        query="Borrego Palm Canyon",
        campground_id="327",
        campground_name="Borrego Palm Canyon (sites 53-89)",
        state="CA",
        country="US",
        booking_url="https://www.reservecalifornia.com/park/2/327",
        area_id="2",
        area_name="Anza-Borrego Desert SP",
        siblings=("327", "329", "330", "776", "777", "2151"),
    ),
    MetadataTarget(
        family="going-to-camp",
        provider_id=12,
        query="Deception Pass",
        campground_id="-2147483624",
        campground_name="Deception Pass State Park",
        state="WA",
        country="US",
        booking_url="https://washington.goingtocamp.com/create-booking/results?resourceLocationId=-2147483624&transactionLocationId=-2147483630",
        area_id="-2147483630",
        area_name="Deception Pass State Park",
        siblings=("-2147483624", "-2147483498"),
    ),
    MetadataTarget(
        family="reserve-america",
        provider_id=13,
        query="Chatfield",
        campground_id="CO_50021",
        campground_name="Chatfield State Park",
        state="CO",
        country="US",
        booking_url="https://www.reserveamerica.com/campgroundDetails.do?contractCode=CO&parkId=50021",
        excluded=("FLST_755487",),
    ),
)


DISCOVERY_TARGETS = (
    TARGETS[0],
    MetadataTarget(
        family="usedirect",
        provider_id=2,
        query="South Camp",
        campground_id="611",
        campground_name="South Camp (sites 1-78)",
        state="CA",
        country="US",
        booking_url="https://www.reservecalifornia.com/park/690/611",
        area_id="690",
        area_name="Pfeiffer Big Sur SP",
        siblings=("611", "612", "767"),
        excluded=("609", "2092", "2093"),
    ),
    *TARGETS[2:],
)


ENRICHMENT_TARGETS = (
    TARGETS[0],
    MetadataTarget(
        family="usedirect",
        provider_id=7,
        query="Lost Dutchman",
        campground_id="64",
        campground_name="Main Campground",
        state="AZ",
        country="US",
        booking_url="https://azstateparks.com/reserve/#!park/13/64",
        area_id="13",
        area_name="Lost Dutchman State Park",
    ),
    MetadataTarget(
        family="reserve-america",
        provider_id=13,
        query="Jackson Lake",
        campground_id="CO_50028",
        campground_name="Jackson Lake State Park",
        state="CO",
        country="US",
        booking_url="https://www.reserveamerica.com/campgroundDetails.do?contractCode=CO&parkId=50028",
    ),
)


for operation, targets in (
    ("discovery", DISCOVERY_TARGETS),
    ("catalog", TARGETS),
    ("enrichment", ENRICHMENT_TARGETS),
):
    if len({target.key for target in targets}) != len(targets):
        raise ValueError(f"{operation}: duplicate provider metadata key")
