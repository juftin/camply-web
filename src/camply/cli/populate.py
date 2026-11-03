"""Compatibility re-exports for database population."""

from camply.cli.db import metadata_cmd
from camply.cli.db import metadata_cmd as populate_database

__all__ = ["metadata_cmd", "populate_database"]
