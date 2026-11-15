"""Canonical saved definitions must preserve native identities and fixed coverage."""

import datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from camply.db.coverage import (
    definition_hash,
    get_or_create_target,
    live_targets,
    normalized_choices,
    reconcile_coverage,
    scan_load_options,
    subscriber_condition,
)
from camply.db.models import (
    Base,
    Campground,
    Provider,
    RecreationArea,
    UniqueTarget,
    User,
    UserScan,
)


def test_definition_identity() -> None:
    """Order, repeats and labels do not change identity; all remains distinct."""
    definition = {
        "provider_id": 1,
        "destination_type": "recreation_area",
        "destination_id": "area",
        "start_date": datetime.date(2027, 7, 1),
        "end_date": datetime.date(2027, 7, 4),
        "coverage_mode": "selected",
    }
    assert definition_hash(
        **definition, selected_ids=[" 001 ", "A", "001"]
    ) == definition_hash(**definition, selected_ids=["A", "001"])
    assert definition_hash(**definition, selected_ids=["001"]) != definition_hash(
        **{**definition, "coverage_mode": "all"}, selected_ids=[]
    )
    assert definition_hash(**definition, selected_ids=["001"]) != definition_hash(
        **{**definition, "provider_id": 2}, selected_ids=["001"]
    )


def test_choice_normalization() -> None:
    """Native IDs keep case and leading zeros while repeated choices collapse."""
    assert normalized_choices([" 001", "A", "001", "a"]) == ["001", "A", "a"]


@pytest.mark.anyio
async def test_reconcile_overlap_unavailable_selections_and_catalog_race() -> None:
    """Overlapping scopes share targets, keep unavailable selections, and detect revision races."""
    import uuid

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    start, end = datetime.date(2027, 7, 1), datetime.date(2027, 7, 4)
    try:
        async with maker() as session:
            provider = Provider(
                id=1, name="Recreation.gov", url="https://recreation.gov"
            )
            area = RecreationArea(id="area", provider_id=1, name="Area")
            cg1 = Campground(
                id="cg1", provider_id=1, recreation_area_id="area", name="Camp 1"
            )
            cg2 = Campground(
                id="cg2", provider_id=1, recreation_area_id="area", name="Camp 2"
            )
            cg3 = Campground(
                id="cg3",
                provider_id=1,
                recreation_area_id="area",
                name="Disabled Camp",
                enabled=False,
            )
            user = User(email="cov@example.test")
            session.add_all([provider, area, cg1, cg2, cg3, user])
            await session.flush()

            cg1_single_target = await get_or_create_target(
                session,
                provider_id=1,
                campground_id="cg1",
                start_date=start,
                end_date=end,
            )
            common = {
                "user_id": user.id,
                "provider_id": 1,
                "start_date": start,
                "end_date": end,
            }
            single = UserScan(
                id=uuid.uuid4(),
                destination_type="campground",
                campground_id="cg1",
                destination_name="Camp 1",
                target_id=cg1_single_target.id,
                coverage=[],
                definition_hash=definition_hash(
                    provider_id=1,
                    destination_type="campground",
                    destination_id="cg1",
                    start_date=start,
                    end_date=end,
                ),
                **common,
            )
            all_scan = UserScan(
                id=uuid.uuid4(),
                destination_type="recreation_area",
                recreation_area_id="area",
                destination_name="Area",
                coverage_mode="all",
                selected_campgrounds=[],
                coverage=[],
                definition_hash=definition_hash(
                    provider_id=1,
                    destination_type="recreation_area",
                    destination_id="area",
                    start_date=start,
                    end_date=end,
                    coverage_mode="all",
                ),
                **common,
            )
            selected_scan = UserScan(
                id=uuid.uuid4(),
                destination_type="recreation_area",
                recreation_area_id="area",
                destination_name="Area",
                coverage_mode="selected",
                selected_campgrounds=[
                    {"id": "cg1", "name": "Camp 1"},
                    {"id": "cg3", "name": "Disabled Camp"},
                ],
                coverage=[],
                definition_hash=definition_hash(
                    provider_id=1,
                    destination_type="recreation_area",
                    destination_id="area",
                    start_date=start,
                    end_date=end,
                    coverage_mode="selected",
                    selected_ids=["cg1", "cg3"],
                ),
                **common,
            )
            session.add_all([single, all_scan, selected_scan])
            await session.flush()
            for scan in (single, all_scan, selected_scan):
                await session.refresh(scan, ["coverage"])
                await reconcile_coverage(session, scan)
            single.target_id = single.coverage[0].target_id
            await session.commit()

        async with maker() as session:
            loaded = (
                (await session.scalars(select(UserScan).options(*scan_load_options())))
                .unique()
                .all()
            )
            by_id = {s.id: s for s in loaded}
            assert len(live_targets(by_id[all_scan.id])) == 2
            assert [t.campground_id for t in live_targets(by_id[selected_scan.id])] == [
                "cg1"
            ]
            assert [i["id"] for i in by_id[selected_scan.id].selected_campgrounds] == [
                "cg1",
                "cg3",
            ]
            cg1_target = next(
                t
                for t in (await session.scalars(select(UniqueTarget))).all()
                if t.campground_id == "cg1"
            )
            subs = (
                await session.scalars(
                    select(UserScan)
                    .join(UniqueTarget, subscriber_condition())
                    .where(UniqueTarget.id == cg1_target.id)
                )
            ).all()
            assert len(subs) == 3

            provider = await session.get(Provider, 1)
            assert provider is not None
            await session.execute(
                update(Provider)
                .where(Provider.id == 1)
                .values(catalog_revision=provider.catalog_revision + 1)
                .execution_options(synchronize_session=False)
            )
            with pytest.raises(ValueError, match="Catalog changed"):
                await reconcile_coverage(session, by_id[all_scan.id])
    finally:
        await engine.dispose()
