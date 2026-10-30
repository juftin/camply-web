"""Report missing optional PostgreSQL support without masking driver failures."""

from unittest.mock import patch

import pytest

from camply.db.config import DatabaseConfig, DatabaseDrivers


def test_missing_postgres_driver_has_installation_hint() -> None:
    """Selecting PostgreSQL explains which public extra supplies its driver."""
    config = DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES)
    with patch(
        "camply.db.config.create_async_engine",
        side_effect=ModuleNotFoundError(name="psycopg"),
    ):
        with pytest.raises(RuntimeError, match=r"camply\[postgres\]"):
            config.create_async_engine()


def test_postgres_internal_import_error_is_preserved() -> None:
    """An installed driver's broken dependency must keep its original traceback."""
    config = DatabaseConfig(DRIVERNAME=DatabaseDrivers.POSTGRES)
    with patch(
        "camply.db.config.create_async_engine",
        side_effect=ModuleNotFoundError(name="synthetic_driver_dependency"),
    ):
        with pytest.raises(ModuleNotFoundError) as error:
            config.create_async_engine()
    assert error.value.name == "synthetic_driver_dependency"
