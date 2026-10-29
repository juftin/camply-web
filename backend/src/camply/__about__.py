"""Shared installed distribution metadata for Camply."""

from importlib.metadata import version

__application__ = "camply"
"""Python distribution and application name."""

__version__ = version(__application__)
"""Installed distribution version shared by all runtimes."""
