"""Opt-in PostgreSQL regression for the revision graph shared by both runtimes."""

import os
import subprocess
import time

import psycopg
import pytest

from db.config import DatabaseConfig, DatabaseDrivers
from db.migrate import upgrade_database


@pytest.mark.skipif(
    os.environ.get("CAMPLY_POSTGRES_SMOKE") != "1",
    reason="Run task backend:migration:test",
)
def test_postgres_populated_upgrade() -> None:
    """Upgrade a populated prior release in a disposable, loopback-only database."""
    container = subprocess.check_output(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--publish",
            "127.0.0.1::5432",
            "--env",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "postgres:17-alpine",
        ],
        text=True,
    ).strip()
    try:
        port = int(
            subprocess.check_output(["docker", "port", container, "5432"], text=True)
            .strip()
            .rsplit(":", 1)[1]
        )
        deadline = time.monotonic() + 30
        while subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", "postgres"],
            capture_output=True,
            check=False,
        ).returncode:
            assert time.monotonic() < deadline, "Test-owned PostgreSQL did not start"
            time.sleep(0.25)
        database = DatabaseConfig(
            DRIVERNAME=DatabaseDrivers.POSTGRES,
            HOST="127.0.0.1",
            PORT=port,
            USERNAME="postgres",
            DATABASE="postgres",
        )
        upgrade_database(database, revision="9b2c3d4e5f6a")
        with psycopg.connect(
            host=database.HOST, port=port, user="postgres", dbname="postgres"
        ) as connection:
            before = connection.execute(
                "SELECT id, name FROM providers ORDER BY id"
            ).fetchall()
        upgrade_database(database)
        upgrade_database(database)
        with psycopg.connect(
            host=database.HOST, port=port, user="postgres", dbname="postgres"
        ) as connection:
            assert (
                connection.execute(
                    "SELECT id, name FROM providers ORDER BY id"
                ).fetchall()
                == before
            )
            assert connection.execute(
                "SELECT COUNT(*) FROM notification_outbox"
            ).fetchone() == (0,)
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container], check=False, capture_output=True
        )
