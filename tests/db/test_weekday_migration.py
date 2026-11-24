"""Preserve existing subscribers through the optional weekday preference migration."""

import datetime
import runpy
from importlib.resources import files
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_weekday_migration_preserves_populated_scans() -> None:
    """Old subscriptions stay unrestricted and survive upgrade/downgrade/re-upgrade."""
    paths = list(files("camply.db").joinpath("migrations/versions").iterdir())
    migration = runpy.run_path(
        str(
            next(
                path for path in paths if path.name.endswith("_add_allowed_weekdays.py")
            )
        )
    )
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            sa.text("CREATE TABLE user_scans (id TEXT, min_stay_length INTEGER)")
        )
        connection.execute(sa.text("INSERT INTO user_scans VALUES ('synthetic', 2)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
            assert (
                connection.execute(
                    sa.text("SELECT allowed_weekdays FROM user_scans")
                ).scalar()
                is None
            )
            connection.execute(
                sa.text("UPDATE user_scans SET allowed_weekdays = '[4,5]'")
            )
            migration["downgrade"]()
            assert connection.execute(sa.text("SELECT * FROM user_scans")).one() == (
                "synthetic",
                2,
            )
            migration["upgrade"]()
            assert (
                connection.execute(
                    sa.text("SELECT allowed_weekdays FROM user_scans")
                ).scalar()
                is None
            )
    engine.dispose()


def test_weekday_migration_compiles_for_postgresql() -> None:
    """The same additive revision emits portable PostgreSQL JSON without table rewrites."""
    import io

    from alembic import command

    from camply.db.config import DatabaseConfig, DatabaseDrivers
    from camply.db.migration import get_alembic_config

    config = get_alembic_config(DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES))
    output = io.StringIO()
    config.output_buffer = output
    command.upgrade(config, revision="d027a1b2c3d4:e818084258e6", sql=True)
    assert "ADD COLUMN allowed_weekdays JSON" in output.getvalue()
    assert "ALTER COLUMN" not in output.getvalue()


def test_weekday_preferences_survive_reopening_storage(tmp_path: Path) -> None:
    """Restricted and legacy unrestricted values persist across database sessions."""
    import uuid

    from sqlalchemy.orm import Session

    from camply.db.models import Base, Provider, UniqueTarget, User, UserScan

    engine = sa.create_engine(f"sqlite:///{tmp_path / 'preferences.db'}")
    Base.metadata.create_all(engine)
    restricted_id = uuid.uuid4()
    unrestricted_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(Provider(id=987, name="Synthetic", url="https://example.test"))
        user = User(email="synthetic@example.test", auth0_id="synthetic-weekday")
        target = UniqueTarget(
            provider_id=987,
            campground_id="synthetic",
            start_date=datetime.date(2099, 7, 1),
            end_date=datetime.date(2099, 9, 1),
        )
        second_target = UniqueTarget(
            provider_id=987,
            campground_id="synthetic-unrestricted",
            start_date=datetime.date(2099, 7, 1),
            end_date=datetime.date(2099, 9, 1),
        )
        session.add_all(
            [
                UserScan(
                    id=restricted_id, user=user, target=target, allowed_weekdays=[4, 5]
                ),
                UserScan(id=unrestricted_id, user=user, target=second_target),
            ]
        )
        session.commit()
    engine.dispose()
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'preferences.db'}")
    with Session(engine) as session:
        assert session.get(UserScan, restricted_id).allowed_weekdays == [4, 5]
        assert session.get(UserScan, unrestricted_id).allowed_weekdays is None
    engine.dispose()
