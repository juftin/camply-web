"""Regression tests for the provider seed migration's data lifecycle."""

import importlib.util
from importlib.resources import files
from types import ModuleType

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, select

from camply.db.models import Base, Campground, Provider


def migration(
    filename: str = "9b94e557767a_seed_reservecalifornia_provider.py",
) -> ModuleType:
    """Load the immutable migration directly without running the application."""
    path = files("camply.db").joinpath("migrations/versions", filename)
    spec = importlib.util.spec_from_file_location("reserve_california_seed", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_empty_catalog_seed_round_trip() -> None:
    """An unused provider seed can upgrade, downgrade, and upgrade again."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration()
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        revision.upgrade()
        assert (
            connection.scalar(select(Provider.name).where(Provider.id == 2))
            == "ReserveCalifornia"
        )
        revision.downgrade()
        assert connection.scalar(select(Provider.id).where(Provider.id == 2)) is None
        revision.upgrade()
        assert (
            connection.scalar(select(Provider.name).where(Provider.id == 2))
            == "ReserveCalifornia"
        )
    engine.dispose()


def test_verified_usedirect_seeds_round_trip() -> None:
    """Bulk seeds match application identities and preserve unrelated providers."""
    from camply.db.data import providers as identities

    expected = [
        identities.FloridaStateParks,
        identities.VirginiaStateParks,
        identities.MinnesotaStateParks,
        identities.OhioStateParks,
        identities.ArizonaStateParks,
        identities.MissouriStateParks,
        identities.FairfaxCountyParks,
        identities.OregonMetro,
        identities.NorthernTerritory,
    ]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration("ea6111bf3bed_seed_verified_usedirect_providers.py")
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        connection.execute(
            insert(Provider).values(id=1, name="Other", url="https://example.com")
        )
        revision.upgrade()
        for provider in expected:
            row = connection.execute(
                select(Provider.__table__).where(Provider.id == provider.id)
            ).one()
            assert (row.name, row.description, row.url, row.enabled) == (
                provider.name,
                provider.description,
                provider.url,
                True,
            )
        revision.downgrade()
        assert connection.scalars(select(Provider.id)).all() == [1]
        revision.upgrade()
        assert len(connection.scalars(select(Provider.id)).all()) == 10
    engine.dispose()


@pytest.mark.parametrize("provider_id", range(3, 12))
def test_usedirect_catalog_blocks_seed_downgrade(provider_id: int) -> None:
    """Every new identity blocks rollback when even one campground depends on it."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration("ea6111bf3bed_seed_verified_usedirect_providers.py")
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        revision.upgrade()
        connection.execute(
            insert(Campground).values(
                id="10", provider_id=provider_id, name="Synthetic campground"
            )
        )
        with pytest.raises(RuntimeError, match=r"UseDirect.*dependent data"):
            revision.downgrade()
        assert len(connection.scalars(select(Provider.id)).all()) == 9
        assert connection.scalar(select(Campground.id)) == "10"
    engine.dispose()


def test_populated_catalog_blocks_seed_downgrade() -> None:
    """SQLite must preserve provider identity even when foreign keys are disabled."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    revision = migration()
    with (
        engine.begin() as connection,
        Operations.context(MigrationContext.configure(connection)),
    ):
        revision.upgrade()
        connection.execute(
            insert(Campground).values(
                id="10", provider_id=2, name="Synthetic campground"
            )
        )
        with pytest.raises(RuntimeError, match=r"ReserveCalifornia.*data"):
            revision.downgrade()
        assert (
            connection.scalar(select(Provider.name).where(Provider.id == 2))
            == "ReserveCalifornia"
        )
        assert (
            connection.scalar(select(Campground.id).where(Campground.provider_id == 2))
            == "10"
        )
    engine.dispose()
