"""
Celery Worker Package and In-Process Scanning Services.
"""

from typing import TYPE_CHECKING, Any

from camply.worker.config import worker_config
from camply.worker.notifications.base import BaseNotificationProvider, NotificationDTO
from camply.worker.notifications.pushover import PushoverProvider

if TYPE_CHECKING:
    from camply.worker.celery_app import celery_app
    from camply.worker.tasks.heartbeat import discover_targets
    from camply.worker.tasks.ingestion import populate_database
    from camply.worker.tasks.notifications import send_pushover_notification
    from camply.worker.tasks.scanner import check_target_availability

__all__ = [
    "BaseNotificationProvider",
    "NotificationDTO",
    "PushoverProvider",
    "celery_app",
    "check_target_availability",
    "discover_targets",
    "populate_database",
    "send_pushover_notification",
    "worker_config",
]

_CELERY_EXPORTS: dict[str, tuple[str, str]] = {
    "celery_app": ("camply.worker.celery_app", "celery_app"),
    "discover_targets": ("camply.worker.tasks.heartbeat", "discover_targets"),
    "populate_database": ("camply.worker.tasks.ingestion", "populate_database"),
    "send_pushover_notification": (
        "camply.worker.tasks.notifications",
        "send_pushover_notification",
    ),
    "check_target_availability": (
        "camply.worker.tasks.scanner",
        "check_target_availability",
    ),
}


def __getattr__(name: str) -> Any:
    """
    Lazily import Celery application and task objects requiring 'distributed'.

    Parameters
    ----------
    name : str
        Attribute name being accessed on the module.

    Returns
    -------
    Any
        The requested Celery task or application instance.

    Raises
    ------
    AttributeError
        If the attribute is not an exported member of the worker package.
    """
    if name in _CELERY_EXPORTS:
        module_name, attr_name = _CELERY_EXPORTS[name]
        import importlib

        module = importlib.import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
