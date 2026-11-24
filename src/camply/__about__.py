"""Shared installed distribution metadata for Camply."""

from importlib.metadata import PackageNotFoundError, version

__application__ = "camply"
"""Python application name."""

__package_name__ = "camply-web"
"""Python distribution name."""

try:
    __version__ = version(__package_name__)
except PackageNotFoundError:  # pragma: no cover
    try:
        __version__ = version(__application__)
    except PackageNotFoundError:
        __version__ = "0.0.0"
"""Installed distribution version shared by all runtimes."""
