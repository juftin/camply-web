"""
Celery Worker Package
"""

from camply.worker.celery_app import celery_app
from camply.worker.config import worker_config
from camply.worker.notifications.base import BaseNotificationProvider, NotificationDTO
from camply.worker.notifications.pushover import PushoverProvider
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
