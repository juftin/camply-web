import asyncio
import time
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, ClassVar, cast
from urllib.parse import urljoin

import platformdirs
import rich.progress
import structlog

from camply.db.config import db
from camply.db.data.providers import RecreationDotGov
from camply.db.models import Provider
from camply.providers.base import BaseProvider
from camply.providers.dto import (
    CampgroundSearchResult,
    CampsiteDTO,
    CampsiteType,
    ProviderSearchQuery,
    ProviderSearchResult,
    RecreationAreaSearchResult,
    SearchEntityType,
)
from camply.providers.recreation_gov.config import RecreationGovConfig
from camply.providers.recreation_gov.models.address import AddressData, AddressPopulator
from camply.providers.recreation_gov.models.api import (
    CampsiteAvailabilityResponse,
    RecDotGovAvailabilityParams,
    RecDotGovCampsite,
    RecDotGovCampsiteResponse,
    RecDotGovCampsiteSearchParams,
    RecDotGovSearchResponse,
    RecDotGovSearchResult,
    RecreationGovCampsiteMetadata,
)
from camply.providers.recreation_gov.models.campgrounds import RecDotGovCampgroundData
from camply.providers.recreation_gov.models.enums import (
    CabinKeywords,
    RecDotGovAvailabilityStatus,
    RecDotGovEquipmentType,
    RVKeywords,
    TentKeywords,
)
from camply.providers.recreation_gov.models.recreation_area import (
    RecDotGovRecreationAreaData,
)
from camply.providers.utils import normalize_country_code, normalize_state_code

_MAX_SEARCH_RECORDS = 500000

logger = structlog.getLogger()


def map_campsite_type(type_str: str | None) -> CampsiteType:
    """
    Map raw campsite type string to standardized CampsiteType enum.
    """
    if not type_str:
        return CampsiteType.OTHER
    type_lower = type_str.lower()
    if any(member.value in type_lower for member in TentKeywords):
        return CampsiteType.TENT
    if any(member.value in type_lower for member in RVKeywords):
        return CampsiteType.RV
    if any(member.value in type_lower for member in CabinKeywords):
        return CampsiteType.CABIN
    return CampsiteType.OTHER


def check_is_electric(campsite: RecDotGovCampsite) -> bool:
    """
    Check if a campsite supports electric hookup.
    """
    if campsite.type and "electric" in campsite.type.lower():
        return True
    for attr in campsite.attributes:
        if (
            "electric" in attr.attribute_name.lower()
            or "electricity" in attr.attribute_name.lower()
        ):
            val = str(attr.attribute_value).lower()
            if val not in ("no", "none", "0", "false", "n/a"):
                return True
    return False


@dataclass
class ZippedDataContents:
    """
    TypedDict for Zipped Data Contents
    """

    json_file: str
    data_model: type[AddressPopulator]
    addresses: str


def _read_catalog(data_file: Path, contents: ZippedDataContents) -> AddressPopulator:
    """Parse large offline JSON/archive data off the application's event loop."""
    with zipfile.ZipFile(data_file, "r") as zipped:
        addresses = AddressData.model_validate_json(
            zipped.read(contents.addresses)
        ).to_mapping()
        parsed = contents.data_model.model_validate_json(
            zipped.read(contents.json_file)
        )
        parsed.ADDRESSES = addresses
        return parsed


class RecreationGovProvider(BaseProvider):
    """
    Recreation.gov Provider Class
    """

    config = RecreationGovConfig()

    @property
    def provider(self) -> Provider:
        """
        Return the provider instance.
        """
        return RecreationDotGov

    async def search_upstream(
        self, query: ProviderSearchQuery
    ) -> list[ProviderSearchResult]:
        """Use upstream relevance and paginate until enough eligible results exist."""
        return await self._search_pages(query)

    async def _complete_search(
        self, query: ProviderSearchQuery
    ) -> list[ProviderSearchResult]:
        """Exhaust native search pages independently of the public display limit."""
        return await self._search_pages(query, complete=True)

    async def get_campground(self, campground_id: str) -> CampgroundSearchResult:
        """Resolve a native campground using exact entity filtering upstream."""
        campground_id = self._native_id(campground_id)
        results = await self._search_pages(
            ProviderSearchQuery(entity_type=SearchEntityType.CAMPGROUND),
            complete=True,
            entity_id=campground_id,
        )
        for result in results:
            if (
                isinstance(result, CampgroundSearchResult)
                and result.campground_id == campground_id
            ):
                return result
        raise ValueError(f"Unknown or unbookable campground ID: {campground_id}")

    async def get_recreation_area(
        self, recreation_area_id: str
    ) -> RecreationAreaSearchResult:
        """Resolve an exact recreation-area entity independently of its children."""
        recreation_area_id = self._native_id(recreation_area_id)
        results = await self._search_pages(
            ProviderSearchQuery(entity_type=SearchEntityType.RECREATION_AREA),
            complete=True,
            entity_id=recreation_area_id,
        )
        for result in results:
            if (
                isinstance(result, RecreationAreaSearchResult)
                and result.recreation_area_id == recreation_area_id
            ):
                return result
        raise ValueError(f"Unknown recreation-area ID: {recreation_area_id}")

    async def filter_campgrounds(
        self,
        campgrounds: list[CampgroundSearchResult],
        *,
        query: str = "",
        state: str | None = None,
    ) -> list[CampgroundSearchResult]:
        """Retain native relevance within bounded batches of selected identities."""
        request = ProviderSearchQuery(
            query=query.strip(),
            state=state.strip().upper() if state is not None else None,
            entity_type=SearchEntityType.CAMPGROUND,
        )
        if not request.query:
            return await super().filter_campgrounds(campgrounds, state=state)
        matched: set[str] = set()
        native_ids = list(dict.fromkeys(c.campground_id for c in campgrounds))
        batch_size = 50
        for start in range(0, len(native_ids), batch_size):
            records = await self._search_pages(
                request,
                complete=True,
                entity_ids=native_ids[start : start + batch_size],
            )
            matched.update(
                result.campground_id
                for result in records
                if isinstance(result, CampgroundSearchResult)
            )
        return [result for result in campgrounds if result.campground_id in matched]

    async def _search_pages(
        self,
        query: ProviderSearchQuery,
        *,
        complete: bool = False,
        entity_id: str | None = None,
        entity_ids: list[str] | None = None,
    ) -> list[ProviderSearchResult]:
        """Validate and aggregate complete pages or stop at a discovery limit."""
        results: dict[tuple[str, str], ProviderSearchResult] = {}
        filters = self._search_filters(query, entity_id, entity_ids)
        start = 0
        expected_total = None
        while True:
            response = await self.async_client.get(
                urljoin(self.config.base_url, self.config.search_endpoint),
                params={
                    "q": query.query,
                    "fq": filters,
                    "start": start,
                    "size": 50,
                },
                headers={**self.headers, "Referer": self.config.referer_header},
                timeout=30.0,
            )
            response.raise_for_status()
            page = RecDotGovSearchResponse.model_validate_json(response.content)
            if page.start != start:
                raise ValueError("Recreation.gov returned an unexpected search page")
            if expected_total is None:
                expected_total = page.total
            if page.total != expected_total:
                raise ValueError("Recreation.gov search changed during pagination")
            for item in page.results:
                result = self._to_search_result(item)
                if result is not None and result.matches(query, match_text=False):
                    results[(item.entity_type, item.entity_id)] = result
            start += len(page.results)
            if (not complete and len(results) >= query.limit) or start >= page.total:
                return list(results.values())
            if not page.results or start >= _MAX_SEARCH_RECORDS:
                raise ValueError("Recreation.gov search pagination made no progress")

    @staticmethod
    def _search_filters(
        query: ProviderSearchQuery,
        entity_id: str | None,
        entity_ids: list[str] | None,
    ) -> list[str]:
        """Keep exact native identities separate from relevance text."""
        filters = [
            {
                "campground": "entity_type:campground",
                "recreation_area": "entity_type:recarea",
                None: "entity_type:(campground OR recarea)",
            }[query.entity_type]
        ]
        if query.entity_type == "campground" and query.recreation_area_id is not None:
            filters.append(f"parent_asset_id:{query.recreation_area_id}")
        if entity_id is not None:
            filters.append(f"entity_id:{entity_id}")
        if entity_ids is not None:
            filters.append(f"entity_id:({' OR '.join(entity_ids)})")
        return filters

    def _to_search_result(
        self, item: RecDotGovSearchResult
    ) -> ProviderSearchResult | None:
        """Translate the two upstream entity types without inventing park parents."""
        if item.entity_type not in {"campground", "recarea"} or not item.name.strip():
            return None
        if item.entity_type == "campground" and not item.reservable:
            return None
        common: dict[str, Any] = {
            "provider_id": self.provider.id,
            "provider_name": self.provider.name,
            "city": item.city,
            "state": normalize_state_code(
                next(
                    (a.state_code for a in item.addresses if a.state_code),
                    item.state_code,
                ),
                "",
            )
            or None,
            "country": normalize_country_code(item.country_code, "") or None,
            "latitude": item.latitude,
            "longitude": item.longitude,
        }
        result: ProviderSearchResult
        if item.entity_type == "recarea":
            result = RecreationAreaSearchResult(
                **common,
                recreation_area_id=item.entity_id,
                recreation_area_name=item.name,
                booking_url=self.get_rec_area_url(item.entity_id),
            )
        else:
            result = CampgroundSearchResult(
                **common,
                campground_id=item.entity_id,
                campground_name=item.name,
                recreation_area_id=item.parent_id,
                recreation_area_name=item.parent_name,
                booking_url=self.get_campground_url(
                    item.entity_id, rec_area_id=item.parent_id
                ),
            )
        return result

    async def sync_metadata(self) -> None:
        """
        Background task to update the database tables.
        """
        await self.populate_database()

    async def paginate_recdotgov_campsites(
        self, facility_id: int
    ) -> list[RecDotGovCampsite]:
        """
        Paginate through the Recreation.gov Campsite Metadata.
        """
        endpoint_url = self.config.campsite_search_url
        fq_list = [f"asset_id:{facility_id}"]
        params = RecDotGovCampsiteSearchParams(
            start=0,
            size=1000,
            fq=fq_list,
            include_non_site_specific_campsites=True,
        )
        campsites: list[RecDotGovCampsite] = []
        continue_paginate = True

        headers = self.headers.copy()
        headers.update(
            {
                "Referer": self.config.referer_header,
                "Accept": "application/json",
            }
        )

        while continue_paginate:
            logger.debug(
                "Fetching campsite metadata page",
                facility_id=facility_id,
                start=params.start,
            )
            response = await self.async_client.get(
                endpoint_url,
                params=params.model_dump(),
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            campsite_response = RecDotGovCampsiteResponse.model_validate_json(
                response.content
            )
            campsites.extend(campsite_response.campsites)
            results = len(campsites)
            params.start = results
            if results >= campsite_response.total or not campsite_response.campsites:
                continue_paginate = False

        return campsites

    async def make_recdotgov_availability_request(
        self,
        campground_id: int,
        month: date,
    ) -> CampsiteAvailabilityResponse:
        """
        Make a monthly availability request to Recreation.gov.
        """
        url = f"{self.config.campsite_availability_url}/{campground_id}/month"
        formatted_month = month.strftime(self.config.api_month_format)
        params = RecDotGovAvailabilityParams(start_date=formatted_month)
        headers = self.headers.copy()
        headers.update(
            {
                "Referer": self.config.referer_header,
                "Accept": "application/json",
            }
        )

        logger.debug(
            "Fetching monthly availability",
            campground_id=campground_id,
            month=formatted_month,
        )
        response = await self.async_client.get(
            url,
            params=params.model_dump(),
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return CampsiteAvailabilityResponse.model_validate_json(response.content)

    async def find_availabilities(
        self,
        park_id: str,
        start_date: date,
        end_date: date,
    ) -> list[CampsiteDTO]:
        """
        Scan and fetch availabilities.
        """
        # Calculate unique months in target range
        months: list[date] = []
        current = date(start_date.year, start_date.month, 1)
        end_month = date(end_date.year, end_date.month, 1)
        december = 12
        while current <= end_month:
            months.append(current)
            if current.month == december:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        facility_id = int(park_id)

        # Parallel fetch of metadata and availabilities
        campsites_task = self.paginate_recdotgov_campsites(facility_id=facility_id)
        availability_tasks = [
            self.make_recdotgov_availability_request(campground_id=facility_id, month=m)
            for m in months
        ]

        results = await asyncio.gather(campsites_task, *availability_tasks)
        campsites = cast(list[RecDotGovCampsite], results[0])
        availability_responses = cast(
            list[CampsiteAvailabilityResponse], list(results[1:])
        )

        metadata_map = {c.campsite_id: c for c in campsites}
        return self._process_availability_responses(
            availability_responses=availability_responses,
            metadata_map=metadata_map,
            start_date=start_date,
            end_date=end_date,
        )

    def _process_availability_responses(
        self,
        availability_responses: list[CampsiteAvailabilityResponse],
        metadata_map: dict[int, RecDotGovCampsite],
        start_date: date,
        end_date: date,
    ) -> list[CampsiteDTO]:
        """
        Process raw monthly availability responses into standardized CampsiteDTOs.
        """
        avail_dto_map: dict[str, CampsiteDTO] = {}
        unavail_statuses = {
            RecDotGovAvailabilityStatus.RESERVED.value,
            RecDotGovAvailabilityStatus.NOT_AVAILABLE.value,
            RecDotGovAvailabilityStatus.NOT_RESERVABLE.value,
            RecDotGovAvailabilityStatus.NOT_RESERVABLE_MANAGEMENT.value,
            RecDotGovAvailabilityStatus.NOT_AVAILABLE_CUTOFF.value,
            RecDotGovAvailabilityStatus.LOTTERY.value,
            RecDotGovAvailabilityStatus.OPEN.value,
            RecDotGovAvailabilityStatus.NYR.value,
            RecDotGovAvailabilityStatus.CLOSED.value,
        }

        for parsed_avail in availability_responses:
            for campsite_id, site_data in parsed_avail.campsites.items():
                self._process_single_campsite(
                    campsite_id=campsite_id,
                    site_data=site_data,
                    metadata_map=metadata_map,
                    start_date=start_date,
                    end_date=end_date,
                    unavail_statuses=unavail_statuses,
                    avail_dto_map=avail_dto_map,
                )

        return list(avail_dto_map.values())

    def _get_available_dates(
        self,
        site_data: Any,
        start_date: date,
        end_date: date,
        unavail_statuses: set[str],
    ) -> list[date]:
        """
        Extract and filter available dates within the target range.
        """
        available_dates = []
        for dt, status in site_data.availabilities.items():
            d = dt.date()
            if start_date <= d <= end_date and status not in unavail_statuses:
                available_dates.append(d)
        return available_dates

    def _create_campsite_dto(
        self,
        campsite_id: int,
        site_data: Any,
        meta_site: RecDotGovCampsite | None,
        available_dates: list[date],
    ) -> CampsiteDTO:
        """
        Create a strongly-typed CampsiteDTO for a campsite.
        """
        campsite_name = site_data.site
        if meta_site:
            campsite_name = meta_site.name or site_data.site

        campsite_type = self._determine_campsite_type(
            site_data=site_data, meta_site=meta_site
        )

        is_accessible = False
        is_electric = False
        capacity = site_data.max_num_people

        if site_data.campsite_type and "electric" in site_data.campsite_type.lower():
            is_electric = True

        permitted_eq = []
        attrs = []
        lat = None
        lon = None
        if meta_site:
            is_accessible = meta_site.accessible
            is_electric = check_is_electric(meta_site) or is_electric
            permitted_eq = meta_site.permitted_equipment
            attrs = meta_site.attributes
            lat = meta_site.latitude
            lon = meta_site.longitude

        metadata_model = RecreationGovCampsiteMetadata(
            loop=site_data.loop,
            site=site_data.site,
            type_of_use=site_data.type_of_use,
            permitted_equipment=permitted_eq,
            attributes=attrs,
            latitude=lat,
            longitude=lon,
        )

        return CampsiteDTO(
            campsite_id=str(campsite_id),
            campsite_name=campsite_name,
            campsite_type=campsite_type,
            capacity=capacity,
            available_dates=sorted(available_dates),
            is_electric=is_electric,
            is_accessible=is_accessible,
            metadata=metadata_model.model_dump(),
        )

    def _process_single_campsite(
        self,
        campsite_id: int,
        site_data: Any,
        metadata_map: dict[int, RecDotGovCampsite],
        start_date: date,
        end_date: date,
        unavail_statuses: set[str],
        avail_dto_map: dict[str, CampsiteDTO],
    ) -> None:
        """
        Process a single campsite's monthly availability.
        """
        available_dates = self._get_available_dates(
            site_data=site_data,
            start_date=start_date,
            end_date=end_date,
            unavail_statuses=unavail_statuses,
        )
        if not available_dates:
            return

        key = str(campsite_id)
        if key in avail_dto_map:
            all_dates = list(set(avail_dto_map[key].available_dates + available_dates))
            all_dates.sort()
            avail_dto_map[key].available_dates = all_dates
        else:
            meta_site = metadata_map.get(campsite_id)
            avail_dto_map[key] = self._create_campsite_dto(
                campsite_id=campsite_id,
                site_data=site_data,
                meta_site=meta_site,
                available_dates=available_dates,
            )

    def _determine_campsite_type(
        self, site_data: Any, meta_site: RecDotGovCampsite | None
    ) -> CampsiteType:
        """
        Determine the standardized campsite type from availability and metadata.
        """
        campsite_type = map_campsite_type(site_data.campsite_type)
        if campsite_type == CampsiteType.OTHER and meta_site:
            campsite_type = map_campsite_type(meta_site.type)
            if campsite_type == CampsiteType.OTHER and meta_site.permitted_equipment:
                eq_names = {
                    eq.equipment_name.lower()
                    for eq in meta_site.permitted_equipment
                    if eq.equipment_name
                }
                rv_keywords = {member.value for member in RecDotGovEquipmentType}
                if any(any(kw in name for kw in rv_keywords) for name in eq_names):
                    return CampsiteType.RV
                elif any(TentKeywords.TENT.value in name for name in eq_names):
                    return CampsiteType.TENT
        return campsite_type

    data_source: ClassVar[str] = RecreationGovConfig().ridb_export_url
    expiration_time: ClassVar[timedelta] = (
        RecreationGovConfig().offline_cache_expiration
    )
    data_files: ClassVar[list[ZippedDataContents]] = [
        ZippedDataContents(
            json_file="RecAreas_API_v1.json",
            addresses="RecAreaAddresses_API_v1.json",
            data_model=RecDotGovRecreationAreaData,
        ),
        ZippedDataContents(
            json_file="Facilities_API_v1.json",
            addresses="FacilityAddresses_API_v1.json",
            data_model=RecDotGovCampgroundData,
        ),
    ]

    async def download_offline_data(self) -> Path:
        """
        Download offline data for the provider.
        """
        download_dir = Path(
            platformdirs.user_data_dir(appname="camply", ensure_exists=True)
        )
        destination_file = download_dir / "RIDBFullExport_V1_JSON.zip"
        if destination_file.exists():
            age = time.time() - destination_file.stat().st_mtime
            age_delta = timedelta(seconds=age)
            if age_delta < self.expiration_time:
                logger.info(
                    "Using cached offline data",
                    provider=self.provider.name,
                )
                return destination_file
        with destination_file.open("wb") as download_file:
            logger.info(
                "Downloading offline data from %s",
                self.data_source,
                provider=self.provider.name,
            )
            logger.info(
                "Saving Offline data to %s",
                destination_file,
                provider=self.provider.name,
            )
            async with self.async_client.stream("GET", self.data_source) as response:
                total = int(response.headers["Content-Length"])
                with rich.progress.Progress(
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    rich.progress.BarColumn(bar_width=None),
                    rich.progress.DownloadColumn(),
                    rich.progress.TransferSpeedColumn(),
                ) as progress:
                    download_task = progress.add_task("Download", total=total)
                    async for chunk in response.aiter_bytes():
                        download_file.write(chunk)
                        progress.update(
                            download_task, completed=response.num_bytes_downloaded
                        )
        return destination_file

    async def populate_database(self) -> None:
        """
        Process the downloaded offline data.
        """
        logger.info(
            "Populating database",
            provider=self.provider.name,
        )
        async with db.get_session() as session:
            if await session.get(Provider, self.provider.id) is None:
                raise RuntimeError(
                    f"Provider {self.provider.name} (ID {self.provider.id}) not found in database. "
                    "Run database migrations before syncing provider metadata."
                )
        async with db.get_session() as session:
            data_file = await self.download_offline_data()
            for data in self.data_files:
                parsed = await asyncio.to_thread(_read_catalog, data_file, data)
                await parsed.to_database(session)
            await self.populate_search_table(session)

    @classmethod
    def get_rec_area_url(cls, rec_area_id: str) -> str:
        """
        Get the URL for a recreation area
        """
        return f"{cls.config.gateway_url_prefix}/{rec_area_id}"

    @classmethod
    def get_campground_url(
        cls, campground_id: str, *, rec_area_id: str | None = None
    ) -> str:
        """
        Get the URL for a campground
        """
        return f"{cls.config.campground_url_prefix}/{campground_id}"
