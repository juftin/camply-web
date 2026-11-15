"""Use installed application wheels with synthetic upstreams, never browser API mocks."""

import datetime as dt
import os

from camply.db.config import db
from camply.db.models import Campground, RecreationArea, Search
from camply.providers import PROVIDERS
from camply.providers.details import DestinationDetails
from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.providers.enrichment import Destination, refresh_destinations
from camply.providers.recreation_gov.provider import RecreationGovProvider
from camply.worker.notifications.pushover import PushoverProvider


class SyntheticProvider(RecreationGovProvider):
    """Keep real provider/session interfaces while supplying generated catalog data."""

    async def populate_database(self) -> None:
        """Create an idempotent synthetic catalog through the installed ORM."""
        async with db.get_session() as session:
            if await session.get(Campground, ("synthetic-cg", 1)) is None:
                session.add(
                    RecreationArea(
                        id="synthetic-area",
                        provider_id=1,
                        name="Synthetic Basin",
                        enabled=True,
                        reservable=True,
                    )
                )
                await session.flush()
                session.add_all(
                    [
                        Campground(
                            id="synthetic-cg",
                            provider_id=1,
                            name="Synthetic Pines",
                            enabled=True,
                            reservable=True,
                        ),
                        Campground(
                            id="synthetic-cg-1",
                            provider_id=1,
                            recreation_area_id="synthetic-area",
                            name="Synthetic Ridge",
                            enabled=True,
                            reservable=True,
                        ),
                        Campground(
                            id="synthetic-cg-2",
                            provider_id=1,
                            recreation_area_id="synthetic-area",
                            name="Synthetic Cove",
                            enabled=True,
                            reservable=True,
                        ),
                    ]
                )
                session.add_all(
                    [
                        Search(
                            id="synthetic-search",
                            entity_type="Campground",
                            provider_id=1,
                            provider_name="Synthetic",
                            campground_id="synthetic-cg",
                            campground_name="Synthetic Pines",
                            latitude=37.7,
                            longitude=-119.6,
                        ),
                        Search(
                            id="synthetic-area-search",
                            entity_type="RecreationArea",
                            provider_id=1,
                            provider_name="Synthetic",
                            recreation_area_id="synthetic-area",
                            recreation_area_name="Synthetic Basin",
                            latitude=37.7,
                            longitude=-119.6,
                        ),
                        Search(
                            id="synthetic-search-1",
                            entity_type="Campground",
                            provider_id=1,
                            provider_name="Synthetic",
                            recreation_area_id="synthetic-area",
                            recreation_area_name="Synthetic Basin",
                            campground_id="synthetic-cg-1",
                            campground_name="Synthetic Ridge",
                            latitude=37.7,
                            longitude=-119.6,
                        ),
                        Search(
                            id="synthetic-search-2",
                            entity_type="Campground",
                            provider_id=1,
                            provider_name="Synthetic",
                            recreation_area_id="synthetic-area",
                            recreation_area_name="Synthetic Basin",
                            campground_id="synthetic-cg-2",
                            campground_name="Synthetic Cove",
                            latitude=37.7,
                            longitude=-119.6,
                        ),
                    ]
                )
                await session.commit()

    async def enrich_metadata(self) -> None:
        """Exercise real cache persistence without downloading a live RIDB archive."""

        async def fetch(destination: Destination) -> DestinationDetails:
            """Provide generated practical details for the test-owned destination."""
            return DestinationDetails(
                source_url=f"https://parks.example.com/{destination.id}",
                fetched_at=dt.datetime.now(dt.timezone.utc),
                directions="Synthetic source directions",
            )

        await refresh_destinations(provider_id=1, fetch=fetch)

    async def find_availabilities(
        self, park_id: str, start_date: dt.date, end_date: dt.date
    ) -> list[CampsiteDTO]:
        """Call a test-owned HTTP provider so slow requests exercise real async I/O."""
        response = await self.async_client.get(
            f"{os.environ['CAMPLY_SYNTHETIC_ORIGIN']}/availability?park_id={park_id}",
            timeout=30,
        )
        response.raise_for_status()
        nights = [
            start_date + dt.timedelta(days=offset)
            for offset in range((end_date - start_date).days)
        ]
        site_id = (
            "synthetic-site"
            if park_id == "synthetic-cg"
            else f"synthetic-site-{park_id}"
        )
        site_name = (
            "Synthetic Site"
            if park_id == "synthetic-cg"
            else f"Synthetic Site {park_id}"
        )
        return [
            CampsiteDTO(
                campsite_id=site_id,
                campsite_name=site_name,
                campsite_type=CampsiteType.TENT,
                capacity=4,
                available_dates=nights,
                is_electric=False,
                is_accessible=False,
            )
        ]


def main() -> None:
    """Start the actual installed launcher after replacing only upstream adapters."""
    PROVIDERS.clear()
    PROVIDERS[1] = SyntheticProvider
    PushoverProvider.config.api_url = os.environ["CAMPLY_SYNTHETIC_ORIGIN"] + "/notify"
    from camply.server.standalone import main as launch

    launch()


if __name__ == "__main__":
    main()
