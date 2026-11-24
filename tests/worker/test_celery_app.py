"""
Tests for the Celery application configuration and task registration.
"""

from camply.worker.celery_app import celery_app
from camply.worker.config import worker_config
from camply.worker.tasks import heartbeat, ingestion, notifications, scanner  # noqa: F401


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_app_name(self) -> None:
        """The Celery app should have the correct name."""
        assert celery_app.main == "camply_worker"

    def test_task_serialization(self) -> None:
        """Task serialization should be msgpack with json acceptance."""
        assert celery_app.conf.task_serializer == "msgpack"
        assert celery_app.conf.result_serializer == "msgpack"
        assert "msgpack" in celery_app.conf.accept_content
        assert "json" in celery_app.conf.accept_content

    def test_timezone_config(self) -> None:
        """Timezone should be UTC."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_task_settings(self) -> None:
        """Task execution settings should be configured."""
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True
        assert celery_app.conf.task_default_retry_delay == 60
        assert celery_app.conf.task_max_retries == 3
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_result_expiry(self) -> None:
        """Results should expire after 1 hour."""
        assert celery_app.conf.result_expires == 3600

    def test_broker_url_set(self) -> None:
        """Broker URL should be configured (may be valkey_url)."""
        assert celery_app.conf.broker_url is not None
        assert isinstance(celery_app.conf.broker_url, str)

    def test_result_backend_set(self) -> None:
        """Result backend should be configured."""
        assert celery_app.conf.result_backend is not None
        assert isinstance(celery_app.conf.result_backend, str)


class TestCeleryTaskRegistration:
    """Tests for task module registration."""

    def test_heartbeat_task_registered(self) -> None:
        """The heartbeat schedule_checks task should be registered."""
        task_name = "search.schedule_checks"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_scanner_task_registered(self) -> None:
        """The scanner check_availability task should be registered."""
        task_name = "search.check_availability"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_notifications_task_registered(self) -> None:
        """The send_pushover task should be registered."""
        task_name = "notifications.send_pushover"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_beat_schedule_configured(self) -> None:
        """The beat schedule should include schedule_checks and catalog.sync_all."""
        beat_schedule = celery_app.conf.beat_schedule
        assert beat_schedule is not None
        assert "schedule-availability-checks" in beat_schedule
        assert (
            beat_schedule["schedule-availability-checks"]["task"]
            == "search.schedule_checks"
        )
        assert (
            beat_schedule["schedule-availability-checks"]["schedule"]
            == worker_config.heartbeat_interval
        )
        assert beat_schedule["schedule-availability-checks"]["schedule"] == 300
        assert "sync-provider-catalogs-daily" in beat_schedule
        assert (
            beat_schedule["sync-provider-catalogs-daily"]["task"] == "catalog.sync_all"
        )

    def test_enrichment_is_scheduled_independently_of_daily_catalogs(self) -> None:
        """Existing unfilled snapshots resume after deployment on every heartbeat."""
        schedule = celery_app.conf.beat_schedule["enrich-provider-details"]
        assert schedule["task"] == "catalog.enrich_all"
        assert schedule["schedule"] == worker_config.heartbeat_interval
        assert "catalog.enrich_all" in celery_app.tasks
        assert "catalog.enrich_provider" in celery_app.tasks
