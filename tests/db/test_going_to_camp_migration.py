"""Regression tests for the Washington State Parks GoingToCamp seed migration."""

import importlib.util
from importlib.resources import files
from types import ModuleType

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, select

from camply.db.data import providers as identities
from camply.db.models import Base, Campground, Provider, RecreationArea, Search


def migration() -> ModuleType:
    """Load the immutable Washington State Parks seed migration directly."""
    path = files("camply.db").joinpath(
        "migrations/versions/c2f84b9d1a3e_seed_washington_going_to_camp_provider.py"
    )
    spec = importlib.util.spec_from_file_location("washington_gtc_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_washington_seed_round_trip() -> None:
    """An unused Washington State Parks seed upgrades, downgrades, and re-upgrades."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration()
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        connection.execute(
            insert(Provider).values(id=1, name="Other", url="https://example.com")
        )
        revision.upgrade()
        row = connection.execute(
            select(Provider.__table__).where(
                Provider.id == identities.WashingtonStateParks.id
            )
        ).one()
        assert (row.name, row.description, row.url, row.enabled) == (
            identities.WashingtonStateParks.name,
            identities.WashingtonStateParks.description,
            identities.WashingtonStateParks.url,
            True,
        )
        revision.downgrade()
        assert connection.scalars(select(Provider.id)).all() == [1]
        revision.upgrade()
        assert sorted(connection.scalars(select(Provider.id)).all()) == [1, 12]
    engine.dispose()


@pytest.mark.parametrize("dependent_kind", ["campground", "recreation_area", "search"])
def test_washington_dependent_rows_block_seed_downgrade(dependent_kind: str) -> None:
    """Dependent rows in catalog or search tables block seed rollback."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration()
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        revision.upgrade()
        if dependent_kind == "campground":
            connection.execute(
                insert(Campground).values(
                    id="-2147483631",
                    provider_id=12,
                    name="Synthetic Campground",
                )
            )
        elif dependent_kind == "recreation_area":
            connection.execute(
                insert(RecreationArea).values(
                    id="-2147483640",
                    provider_id=12,
                    name="Synthetic Park",
                )
            )
        else:
            connection.execute(
                insert(Search).values(
                    id="RecreationArea/12/-2147483640/",
                    entity_type="RecreationArea",
                    provider_id=12,
                    provider_name="Washington State Parks",
                    recreation_area_id="-2147483640",
                    recreation_area_name="Synthetic Park",
                    reservable=True,
                )
            )
        with pytest.raises(
            RuntimeError, match=r"Washington State Parks.*dependent data"
        ):
            revision.downgrade()
        assert (
            connection.scalar(select(Provider.name).where(Provider.id == 12))
            == "Washington State Parks"
        )
    engine.dispose()


def verified_gtc_migration() -> ModuleType:
    """Load the immutable verified GoingToCamp batch seed migration directly."""
    path = files("camply.db").joinpath(
        "migrations/versions/2d7ab29d3a46_seed_verified_going_to_camp_providers.py"
    )
    spec = importlib.util.spec_from_file_location("verified_gtc_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verified_going_to_camp_seed_round_trip() -> None:
    """Unused verified GoingToCamp seeds upgrade, downgrade, and re-upgrade cleanly."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = verified_gtc_migration()
    expected = [
        identities.WisconsinStateParks,
        identities.MichiganStateParks,
        identities.TacomaPowerParks,
        identities.ParksCanada,
        identities.BCParks,
        identities.OntarioParks,
        identities.NovaScotiaParks,
        identities.ManitobaParks,
        identities.NewfoundlandAndLabradorParks,
        identities.GatineauPark,
        identities.LongPointRegion,
        identities.MaitlandValley,
        identities.StClairRegion,
    ]
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        connection.execute(
            insert(Provider).values(id=1, name="Other", url="https://example.com")
        )
        revision.upgrade()
        rows = connection.execute(
            select(Provider.__table__).where(Provider.id >= 14).order_by(Provider.id)
        ).all()
        assert [
            (row.id, row.name, row.description, row.url, row.enabled) for row in rows
        ] == [
            (item.id, item.name, item.description, item.url, True) for item in expected
        ]
        revision.downgrade()
        assert connection.scalars(select(Provider.id)).all() == [1]
        revision.upgrade()
        assert sorted(connection.scalars(select(Provider.id)).all()) == [
            1,
            *range(14, 27),
        ]
    engine.dispose()


@pytest.mark.parametrize("dependent_kind", ["campground", "recreation_area", "search"])
def test_verified_going_to_camp_dependent_rows_block_downgrade(
    dependent_kind: str,
) -> None:
    """Dependent catalog or search rows block rollback of the GoingToCamp batch seed."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = verified_gtc_migration()
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        revision.upgrade()
        if dependent_kind == "campground":
            connection.execute(
                insert(Campground).values(
                    id="-2147483631",
                    provider_id=17,
                    name="Synthetic Parks Canada Campground",
                )
            )
        elif dependent_kind == "recreation_area":
            connection.execute(
                insert(RecreationArea).values(
                    id="-2147483640",
                    provider_id=17,
                    name="Synthetic National Park",
                )
            )
        else:
            connection.execute(
                insert(Search).values(
                    id="RecreationArea/17/-2147483640/",
                    entity_type="RecreationArea",
                    provider_id=17,
                    provider_name="Parks Canada",
                    recreation_area_id="-2147483640",
                    recreation_area_name="Synthetic National Park",
                    reservable=True,
                )
            )
        with pytest.raises(
            RuntimeError, match=r"GoingToCamp providers have dependent data"
        ):
            revision.downgrade()
        assert (
            connection.scalar(select(Provider.name).where(Provider.id == 17))
            == "Parks Canada"
        )
    engine.dispose()
