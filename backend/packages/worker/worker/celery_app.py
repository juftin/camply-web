"""
Celery Application Configuration
"""

import structlog
from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging, worker_ready

from worker.config import worker_config

logger = structlog.getLogger(__name__)


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application instance.
    """
    app = Celery("camply_worker")

    # Broker and result backend both point at Valkey
    app.conf.broker_url = worker_config.valkey_url
    app.conf.result_backend = worker_config.valkey_url

    # Task serialization: JSON only (secure, debuggable, no pickle)
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]

    # Timezone
    app.conf.timezone = "UTC"
    app.conf.enable_utc = True

    # Task settings
    app.conf.task_track_started = True
    app.conf.task_acks_late = True
    app.conf.task_reject_on_worker_lost = True
    app.conf.task_default_retry_delay = 60  # 1 minute
    app.conf.task_max_retries = 3

    # Result expiry: 1 hour (we don't need results long-term)
    app.conf.result_expires = 3600

    # Beat schedule:
    # - discover_targets every 60 seconds
    # - populate_database daily at midnight UTC
    app.conf.beat_schedule = {
        "discover-targets-every-60s": {
            "task": "worker.tasks.heartbeat.discover_targets",
            "schedule": worker_config.heartbeat_interval,
        },
        "populate-database-daily": {
            "task": "worker.tasks.ingestion.populate_database",
            "schedule": crontab(minute=0, hour=0),
        },
    }

    # Module containing task definitions (autodiscovery)
    app.conf.imports = [
        "worker.tasks.heartbeat",
        "worker.tasks.ingestion",
        "worker.tasks.scanner",
        "worker.tasks.notifications",
    ]

    return app


@setup_logging.connect
def configure_celery_logging(**kwargs: object) -> None:
    """
    Override Celery's default logging to use structlog.

    Celery's default logging setup wipes all existing handlers
    and configures its own. We reconnect structlog after it runs.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


celery_app = create_celery_app()

# Import metrics module to register Celery signal handlers (task_prerun, task_postrun)
import worker.metrics  # noqa: E402, F401


@worker_ready.connect
def _on_worker_ready(**kwargs: object) -> None:
    """Start the Prometheus metrics HTTP server when the worker is ready."""
    if worker_config.metrics_port > 0:
        from worker.metrics import start_metrics_server_in_thread

        start_metrics_server_in_thread(port=worker_config.metrics_port)


# Conditional Sentry initialization
if worker_config.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=worker_config.sentry_dsn,
        traces_sample_rate=worker_config.sentry_traces_sample_rate,
        integrations=[CeleryIntegration()],
        environment=worker_config.environment,
    )
    logger.info("Sentry initialized for Celery worker")
