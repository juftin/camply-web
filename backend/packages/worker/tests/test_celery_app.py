"""
Tests for the Celery application configuration and task registration.
"""

from worker.celery_app import celery_app


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration."""

    def test_app_name(self) -> None:
        """The Celery app should have the correct name."""
        assert celery_app.main == "camply_worker"

    def test_task_serialization(self) -> None:
        """Task serialization should be JSON for security."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

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
        """The heartbeat discover_targets task should be registered."""
        task_name = "worker.tasks.heartbeat.discover_targets"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_scanner_task_registered(self) -> None:
        """The scanner check_target_availability task should be registered."""
        task_name = "worker.tasks.scanner.check_target_availability"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_notifications_task_registered(self) -> None:
        """The send_pushover_notification task should be registered."""
        task_name = "worker.tasks.notifications.send_pushover_notification"
        registered_tasks = list(celery_app.tasks.keys())
        assert task_name in registered_tasks

    def test_beat_schedule_configured(self) -> None:
        """The beat schedule should include discover_targets."""
        beat_schedule = celery_app.conf.beat_schedule
        assert beat_schedule is not None
        assert "discover-targets-every-60s" in beat_schedule
        assert (
            beat_schedule["discover-targets-every-60s"]["task"]
            == "worker.tasks.heartbeat.discover_targets"
        )
