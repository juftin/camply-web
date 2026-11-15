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


def test_area_scan_attributed_results_and_unavailable_metadata(
    test_client: TestClient,
) -> None:
    """Area results attribute identical campsite IDs per campground and tolerate stale/disabled metadata."""
    import datetime as dt

    from camply.db.models import RecreationArea, UniqueTarget

    area_id = f"area-res-{uuid.uuid4().hex[:8]}"
    cg_a = f"cg-a-{uuid.uuid4().hex[:8]}"
    cg_b = f"cg-b-{uuid.uuid4().hex[:8]}"
    conftest.seed_data(
        add_rows=[
            RecreationArea(id=area_id, provider_id=1, name="Attributed Area"),
            Campground(
                id=cg_a,
                provider_id=1,
                recreation_area_id=area_id,
                name="Alpha Basin",
                enabled=True,
                reservable=True,
            ),
            Campground(
                id=cg_b,
                provider_id=1,
                recreation_area_id=area_id,
                name="Beta Basin",
                enabled=True,
                reservable=True,
            ),
        ]
    )
    created = test_client.post(
        "/api/scans",
        json={
            "provider_id": 1,
            "destination_type": "recreation_area",
            "recreation_area_id": area_id,
            "coverage_mode": "selected",
            "campground_ids": [cg_a, cg_b],
            "start_date": "2027-07-01",
            "end_date": "2027-07-05",
            "min_stay_length": 1,
        },
    )
    assert created.status_code == 201, created.text
    scan_id = created.json()["id"]

    async def seed_member_results() -> None:
        from sqlalchemy import update as sa_update

        from camply.db.models import ScanTarget

        async with conftest.maker() as session:
            targets = (
                await session.scalars(
                    select(UniqueTarget).where(
                        UniqueTarget.campground_id.in_([cg_a, cg_b])
                    )
                )
            ).all()
            by_cg = {target.campground_id: target for target in targets}
            by_cg[cg_a].last_checked_at = dt.datetime.now(dt.timezone.utc)
            by_cg[cg_b].last_checked_at = dt.datetime.now(dt.timezone.utc)
            by_cg[cg_b].attempt_error_category = "timeout"
            await session.execute(
                sa_update(ScanTarget)
                .where(ScanTarget.scan_id == uuid.UUID(scan_id))
                .values(outcome="success")
            )
            session.add_all(
                [
                    ScanResult(
                        target_id=by_cg[cg_a].id,
                        campsite_id="001",
                        campsite_name="Loop A Site 1",
                        campsite_type="TENT",
                        is_electric=False,
                        is_accessible=False,
                        available_dates=["2027-07-01", "2027-07-02"],
                    ),
                    ScanResult(
                        target_id=by_cg[cg_b].id,
                        campsite_id="001",
                        campsite_name="Loop B Site 1",
                        campsite_type="RV",
                        is_electric=True,
                        is_accessible=False,
                        available_dates=["2027-07-02"],
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed_member_results())
    detail = test_client.get(f"/api/scans/{scan_id}").json()
    assert detail["found_count"] == 2
    assert detail["matching_campground_count"] == 2
    assert detail["checked_campground_count"] == 2
    assert detail["failed_campground_count"] == 0
    assert [
        (r["campground_id"], r["campground_name"], r["campsite_id"], r["is_stale"])
        for r in detail["results"]
    ] == [
        (cg_a, "Alpha Basin", "001", False),
        (cg_b, "Beta Basin", "001", True),
    ]
    assert [m["outcome"] for m in detail["campgrounds"]] == ["success", "success"]

    # Disable cg_b in catalog: preserved selection retains its saved name as unavailable,
    # and stale results drop from active matches cleanly.
    async def disable_cg_b() -> None:
        async with conftest.maker() as session:
            cg = await session.get(Campground, (cg_b, 1))
            assert cg is not None
            cg.enabled = False
            await session.commit()

    asyncio.run(disable_cg_b())
    after_disable = test_client.get(f"/api/scans/{scan_id}").json()
    assert after_disable["found_count"] == 1
    assert after_disable["unavailable_selection_count"] == 1
    disabled_member = next(
        m for m in after_disable["campgrounds"] if m["campground_id"] == cg_b
    )
    assert disabled_member["campground_name"] == "Beta Basin"
    assert disabled_member["eligible"] is False
