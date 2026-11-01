"""Verify migration checkpoints cannot turn a failed migration into a successful gate."""

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def runner() -> ModuleType:
    """Load the exact migration script mounted into the chart's Job."""
    path = Path(__file__).resolve().parents[2] / "deploy/helm/files/migrate.py"
    spec = importlib.util.spec_from_file_location("camply_chart_migrate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def connection(runner: ModuleType, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Supply a synthetic database with no previous successful checkpoint."""
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = None
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(runner.psycopg, "connect", connect)
    monkeypatch.setattr(runner, "upgrade", MagicMock())
    return connection


def test_completed_migration_skips_older_graph(
    runner: ModuleType, connection: MagicMock
) -> None:
    """A rollback can finish even when its installed Alembic graph is now older."""
    connection.execute.return_value.fetchone.return_value = (1,)
    runner.upgrade.side_effect = RuntimeError("Unknown newer Alembic revision")
    runner.migrate("previous-job")
    runner.upgrade.assert_not_called()
    assert connection.execute.call_args.args[1] == ("previous-job",)
    assert not any(
        call.args[0].startswith("INSERT") for call in connection.execute.call_args_list
    )


def test_success_recorded_after_migration(
    runner: ModuleType, connection: MagicMock
) -> None:
    """New Jobs execute Alembic before making their checkpoint visible."""
    events: list[str] = []
    runner.upgrade.side_effect = lambda: events.append("upgrade")

    def execute(statement: str, parameters: tuple[str, ...] | None = None) -> MagicMock:
        """Observe checkpoint writes without needing a live database."""
        if statement.startswith("INSERT"):
            assert events == ["upgrade"]
            assert parameters == ("new-job",)
            events.append("checkpoint")
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        return cursor

    connection.execute.side_effect = execute
    runner.migrate("new-job")
    assert events == ["upgrade", "checkpoint"]
    runner.psycopg.connect.assert_called_once()
    assert runner.psycopg.connect.call_args.kwargs["autocommit"] is True


def test_failed_migration_never_records_success(
    runner: ModuleType, connection: MagicMock
) -> None:
    """A failed or incomplete migration remains retryable and blocks consumers."""
    runner.upgrade.side_effect = RuntimeError("Migration failed")
    with pytest.raises(RuntimeError, match="Migration failed"):
        runner.migrate("failed-job")
    assert not any(
        call.args[0].startswith("INSERT") for call in connection.execute.call_args_list
    )


def test_checkpoint_database_failure_stops_migration(
    runner: ModuleType, connection: MagicMock
) -> None:
    """Checkpoint lookup failures fail closed rather than assuming a prior success."""
    connection.execute.side_effect = RuntimeError("Database unavailable")
    with pytest.raises(RuntimeError, match="Database unavailable"):
        runner.migrate("new-job")
    runner.upgrade.assert_not_called()
