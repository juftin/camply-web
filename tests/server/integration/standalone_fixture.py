"""Use installed application wheels with synthetic upstreams, never browser API mocks."""

import datetime as dt
import os

from camply.db.config import db
from camply.db.models import Campground, Search
from camply.providers import PROVIDERS
from camply.providers.dto import CampsiteDTO, CampsiteType
from camply.providers.recreation_gov.provider import RecreationGovProvider
from camply.worker.notifications.pushover import PushoverProvider


class SyntheticProvider(RecreationGovProvider):
    """Keep real provider/session interfaces while supplying generated catalog data."""

    async def populate_database(self) -> None:
        """Create an idempotent synthetic catalog through the installed ORM."""
        async with db.get_session() as session:
            if await session.get(Campground, ("synthetic-cg", 1)) is None:
                session.add(
                    Campground(id="synthetic-cg", provider_id=1, name="Synthetic Pines")
                )
                session.add(
                    Search(
                        id="synthetic-search",
                        entity_type="Campground",
                        provider_id=1,
                        provider_name="Synthetic",
                        campground_id="synthetic-cg",
                        campground_name="Synthetic Pines",
                        latitude=37.7,
                        longitude=-119.6,
                    )
                )
                await session.commit()

    async def find_availabilities(
        self, park_id: str, start_date: dt.date, end_date: dt.date
    ) -> list[CampsiteDTO]:
        """Call a test-owned HTTP provider so slow requests exercise real async I/O."""
        response = await self.async_client.get(
            os.environ["CAMPLY_SYNTHETIC_ORIGIN"] + "/availability", timeout=30
        )
        response.raise_for_status()
        nights = [
            start_date + dt.timedelta(days=offset)
            for offset in range((end_date - start_date).days)
        ]
        return [
            CampsiteDTO(
                campsite_id="synthetic-site",
                campsite_name="Synthetic Site",
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
