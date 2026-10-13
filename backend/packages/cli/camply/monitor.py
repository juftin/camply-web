"""
Monitoring engine for continuous polling and availability alerting.
"""

import asyncio
from datetime import date, datetime
from typing import Callable

import structlog

from camply.config import CamplySettings
from camply.output import print_banner, print_info
from camply_core.availability import AvailabilitySnapshot, diff_new_openings
from camply_core.matching import matches_filters
from camply_core.models import CampsiteDTO, NotificationDTO, SearchFilters, SearchWindow
from camply_core.notifications.pushover import PushoverClient
from camply_core.providers.recreation_gov import RecreationGovClient

logger = structlog.getLogger(__name__)


class AvailabilityMonitor:
    """
    Continuous poller that checks campgrounds for availability and dispatches alerts.

    Parameters
    ----------
    campground_ids : list[int]
        Campground facility IDs to check.
    search_window : SearchWindow
        Arrival and departure date boundaries.
    filters : SearchFilters
        Stay requirements such as consecutive nights and equipment.
    continuous : bool
        Whether to loop continuously until stopped.
    polling_interval_minutes : int
        Minutes to wait between polling cycles.
    notifications : list[str]
        Enabled notification channels (e.g. 'pushover', 'silent').
    settings : CamplySettings
        Application settings with credentials.
    """

    def __init__(
        self,
        campground_ids: list[int],
        search_window: SearchWindow,
        filters: SearchFilters,
        continuous: bool = False,
        polling_interval_minutes: int = 10,
        notifications: list[str] | None = None,
        settings: CamplySettings | None = None,
    ) -> None:
        self.campground_ids = campground_ids
        self.search_window = search_window
        self.filters = filters
        self.continuous = continuous
        self.polling_interval_seconds = max(polling_interval_minutes, 1) * 60
        self.notifications = notifications or []
        self.settings = settings or CamplySettings()
        self.client = RecreationGovClient()
        self.previous_snapshot: AvailabilitySnapshot | None = None

    async def execute_cycle(self) -> list[CampsiteDTO]:
        """
        Execute a single polling check across all target campgrounds.

        Returns
        -------
        list[CampsiteDTO]
            All currently available and filter-matching campsite entries.
        """
        all_availabilities: list[CampsiteDTO] = []

        for cid in self.campground_ids:
            try:
                results = await self.client.find_availabilities(
                    park_id=str(cid),
                    start_date=self.search_window.arrival,
                    end_date=self.search_window.departure,
                )
                filtered = [
                    site for site in results if matches_filters(site, self.filters)
                ]
                all_availabilities.extend(filtered)
            except Exception as exc:
                logger.error(
                    "Error querying campground availability",
                    campground_id=cid,
                    error=str(exc),
                )

        current_snapshot = AvailabilitySnapshot.from_campsites(all_availabilities)

        new_openings = diff_new_openings(self.previous_snapshot, current_snapshot)
        self.previous_snapshot = current_snapshot

        if new_openings and "pushover" in self.notifications:
            await self._dispatch_pushover_alerts(all_availabilities, new_openings)

        return all_availabilities

    async def _dispatch_pushover_alerts(
        self,
        campsites: list[CampsiteDTO],
        new_openings: dict[str, set[date]],
    ) -> None:
        """
        Send Pushover alerts for newly detected openings.

        Parameters
        ----------
        campsites : list[CampsiteDTO]
            Current qualifying campsite records.
        new_openings : dict[str, set[date]]
            Mapping of campsite_id to set of newly available dates.
        """
        if not self.settings.pushover_user_key or not self.settings.pushover_app_token:
            logger.warning(
                "Pushover notification requested but credentials not configured."
            )
            return

        pushover = PushoverClient(app_token=self.settings.pushover_app_token)
        new_site_ids = set(new_openings.keys())

        for site in campsites:
            if site.campsite_id in new_site_ids:
                notification = NotificationDTO(
                    title=f"Campsite Available: {site.campsite_name}",
                    message=(
                        f"{site.campsite_name} ({site.campsite_type.value}) is available for "
                        f"{len(site.available_dates)} night(s)!"
                    ),
                    booking_url=site.booking_url
                    or self.client.get_campground_url(site.campsite_id),
                    park_name=f"Campground {site.campsite_id}",
                    campsite_name=site.campsite_name,
                    start_date=self.search_window.arrival,
                    end_date=self.search_window.departure,
                )
                try:
                    await pushover.send_alert(
                        user_key=self.settings.pushover_user_key,
                        payload=notification,
                    )
                except Exception as exc:
                    logger.error("Failed to send Pushover alert", error=str(exc))

    async def run(
        self,
        on_results: Callable[[list[CampsiteDTO]], None] | None = None,
    ) -> list[CampsiteDTO]:
        """
        Run monitoring loop according to continuous settings.

        Parameters
        ----------
        on_results : Callable[[list[CampsiteDTO]], None] | None
            Optional callback invoked on each cycle's findings.

        Returns
        -------
        list[CampsiteDTO]
            Final batch of availabilities discovered.
        """
        cycle_count = 0
        while True:
            cycle_count += 1
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print_info(
                f"[{now_str}] Polling cycle #{cycle_count} checking campgrounds {self.campground_ids}..."
            )

            results = await self.execute_cycle()
            if on_results:
                on_results(results)

            if not self.continuous:
                return results

            if results:
                print_banner(
                    title="🎉 Campsites Found!",
                    message=f"Discovered {len(results)} matching campsite opening(s)!",
                )

            print_info(
                f"Sleeping for {self.polling_interval_seconds // 60} minute(s) before next check. (Press Ctrl+C to exit)"
            )
            try:
                await asyncio.sleep(self.polling_interval_seconds)
            except asyncio.CancelledError:
                break

        return []
