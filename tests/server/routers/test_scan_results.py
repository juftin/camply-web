"""Verify matching results, booking actions and counts from persisted snapshots."""

import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from camply.db.models import Campground, ScanResult, UserScan
from tests.server import conftest


def test_results_match_saved_filters_and_counts(test_client: TestClient) -> None:
    """Return named matching stays and consistent list/detail/update counts."""
    campground_id = f"results-{uuid.uuid4().hex}"
    conftest.seed_data(
        add_rows=[
            Campground(
                id=campground_id,
                provider_id=1,
                name="Synthetic Results Camp",
            )
        ]
    )
    created = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "campground_id": campground_id,
            "start_date": "2027-07-01",
            "end_date": "2027-07-10",
            "min_stay_length": 2,
            "require_electric": True,
            "preferred_types": ["RV"],
        },
    ).json()
    scan_id = created["id"]

    async def seed_snapshots() -> None:
        """Write provider attributes without making external provider requests."""
        async with conftest.maker() as session:
            scan = await session.scalar(
                select(UserScan).where(UserScan.id == uuid.UUID(scan_id))
            )
            assert scan is not None
            session.add_all(
                [
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="match",
                        campsite_name="Site 042",
                        campsite_type="RV",
                        is_electric=True,
                        is_accessible=True,
                        available_dates=["2027-07-01", "2027-07-05"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="match",
                        campsite_name="Site 042",
                        campsite_type="RV",
                        is_electric=True,
                        is_accessible=True,
                        available_dates=["2027-07-02"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="tent",
                        campsite_name="Site 043",
                        campsite_type="TENT",
                        is_electric=True,
                        available_dates=["2027-07-01", "2027-07-02"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="dry",
                        campsite_type="RV",
                        is_electric=False,
                        available_dates=["2027-07-01", "2027-07-02"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="short",
                        campsite_type="RV",
                        is_electric=True,
                        available_dates=["2027-07-01", "2027-07-03"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="legacy",
                        available_dates=["2027-07-01", "2027-07-02"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="expired",
                        campsite_type="RV",
                        is_electric=True,
                        available_dates=["2000-01-01", "2000-01-02"],
                    ),
                    ScanResult(
                        target_id=scan.target_id,
                        campsite_id="outside-range",
                        campsite_type="RV",
                        is_electric=True,
                        available_dates=["2027-07-10", "2027-07-11"],
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed_snapshots())
    response = test_client.get(f"/api/scans/{scan_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["found_count"] == 1
    result = detail["results"][0]
    assert result["campsite_name"] == "Site 042"
    assert result["campsite_type"] == "RV"
    assert result["is_electric"] is True
    assert result["is_accessible"] is True
    assert result["available_dates"] == ["2027-07-01", "2027-07-02"]
    assert (
        result["booking_url"]
        == f"https://www.recreation.gov/camping/campgrounds/{campground_id}"
    )
    listed = test_client.get("/api/scans?limit=200").json()["scans"]
    assert next(scan for scan in listed if scan["id"] == scan_id)["found_count"] == 1
    updated = test_client.patch(
        f"/api/scans/{scan_id}", json={"require_electric": False}
    ).json()
    assert updated["found_count"] == 2
    test_client.patch(f"/api/scans/{scan_id}", json={"preferred_types": []})
    relaxed = test_client.get(f"/api/scans/{scan_id}").json()
    assert relaxed["found_count"] == 4
    legacy = next(
        site for site in relaxed["results"] if site["campsite_id"] == "legacy"
    )
    assert legacy["campsite_name"] == ""
    assert legacy["campsite_type"] is None
