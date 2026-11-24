"""Remember successful migration Jobs in their database so rollback can reuse them."""

import argparse

import psycopg

from camply.db.config import db
from camply.db.migration import upgrade


def migrate(job_name: str) -> None:
    """Run unrecorded migrations; record success only after Alembic finishes.

    The checkpoint lives alongside the schema it describes. A recreated rollback
    Job can therefore finish without asking an older image to resolve a newer
    Alembic revision. New databases have no checkpoints and always run migrations.
    """
    with psycopg.connect(
        host=db.HOST,
        port=db.PORT,
        user=db.USERNAME,
        password=db.PASSWORD,
        dbname=db.DATABASE,
        autocommit=True,
    ) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS camply_helm_migrations "
            "(job_name text PRIMARY KEY, completed_at timestamptz NOT NULL DEFAULT now())"
        )
        if connection.execute(
            "SELECT 1 FROM camply_helm_migrations WHERE job_name = %s", (job_name,)
        ).fetchone():
            return
        upgrade()
        connection.execute(
            "INSERT INTO camply_helm_migrations (job_name) VALUES (%s) "
            "ON CONFLICT (job_name) DO NOTHING",
            (job_name,),
        )


def main() -> None:
    """Use the exact Job identity from the rendered release as its checkpoint key."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    migrate(parser.parse_args().job)


if __name__ == "__main__":
    main()
