"""
Celery Worker Package
"""

from worker.celery_app import celery_app
from worker.config import worker_config
from worker.notifications.base import BaseNotificationProvider, NotificationDTO
from worker.notifications.pushover import PushoverProvider
from worker.tasks.heartbeat import discover_targets
from worker.tasks.ingestion import populate_database
from worker.tasks.notifications import send_pushover_notification
from worker.tasks.scanner import check_target_availability

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
