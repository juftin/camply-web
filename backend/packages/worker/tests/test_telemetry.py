"""
Tests for worker task telemetry and discovery completion metadata.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from celery.signals import task_failure

from worker.telemetry import (
    _extract_entity_info,
    _normalize_outcome,
    record_discovery_completion,
    record_task_execution,
)


def test_failed_attempt_is_recorded_once_with_original_duration() -> None:
    """Celery failure followed by post-run emits one outcome with its worker and duration."""
    from worker import telemetry

    task = SimpleNamespace(
        name="synthetic.task", request=SimpleNamespace(hostname="worker-1", retries=0)
    )
    with (
        patch.object(telemetry, "record_task_execution") as record,
        patch.object(telemetry.time, "monotonic", side_effect=[10.0, 12.0, 13.0]),
    ):
        telemetry._on_telemetry_prerun(task_id="failed-attempt")
        task_failure.send(
            sender=task,
            task_id="failed-attempt",
            exception=ValueError("synthetic"),
            args=(),
            kwargs={},
        )
        telemetry._on_telemetry_postrun(
            task=task, task_id="failed-attempt", state="FAILURE"
        )
    record.assert_called_once()
    assert record.call_args.kwargs["start_time"] == 10.0
    assert record.call_args.kwargs["worker"] == "worker-1"


def test_extract_entity_info() -> None:
    assert _extract_entity_info({"target_id": "tgt-1"}, ()) == ("target", "tgt-1")
    assert _extract_entity_info({"scan_id": "scn-1"}, ()) == ("scan", "scn-1")
    assert _extract_entity_info({"user_id": "usr-1"}, ()) == ("user", "usr-1")
    assert _extract_entity_info({}, ()) == (None, None)


def test_normalize_outcome() -> None:
    # Success with normal return
    outcome, reason = _normalize_outcome("SUCCESS", {"found": 3})
    assert outcome == "success"
    assert reason is None

    # Success with skipped return
    outcome, reason = _normalize_outcome(
        "SUCCESS", {"status": "skipped", "reason": "lock_held"}
    )
    assert outcome == "skipped"
    assert reason == "lock_held"

    # Success with error return
    outcome, reason = _normalize_outcome(
        "SUCCESS", {"status": "error", "reason": "target_not_found"}
    )
    assert outcome == "error"
    assert reason == "target_not_found"

    # Retry exception
    retry_exc = Retry(message="Temporary error")
    outcome, reason = _normalize_outcome("RETRY", None, exception=retry_exc)
    assert outcome == "retrying"
    assert reason == "task_retry"

    # Generic failure
    outcome, reason = _normalize_outcome(
        "FAILURE", None, exception=ValueError("Invalid")
    )
    assert outcome == "error"
    assert reason == "exception"


def test_record_task_execution_writes_to_redis() -> None:
    mock_redis = MagicMock()
    with patch("worker.telemetry.get_redis_client", return_value=mock_redis):
        record_task_execution(
            task_id="t-123",
            task_name="search.check-availability",
            worker="worker-1",
            start_time=100.0,
            finish_time=100.25,
            state="SUCCESS",
            retval={"status": "success"},
            kwargs={"target_id": "target-uuid-1"},
        )

        assert mock_redis.xadd.called
        stream_call = mock_redis.xadd.call_args
        stream_key, record = stream_call[0]
        assert stream_key == "camply:telemetry:tasks"
        assert record["task_id"] == "t-123"
        assert record["entity_type"] == "target"
        assert record["entity_id"] == "target-uuid-1"
        assert record["outcome"] == "success"
        assert record["duration_ms"] == 250.0

        assert mock_redis.setex.called
        key_call = mock_redis.setex.call_args
        assert key_call[0][0] == "camply:telemetry:task:t-123"


def test_record_task_execution_records_provider_and_search_metadata() -> None:
    """
    Task telemetry records provider and search metadata.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    mock_redis = MagicMock()
    with patch("worker.telemetry.get_redis_client", return_value=mock_redis):
        record_task_execution(
            task_id="t-999",
            task_name="search.check-availability",
            worker="worker-1",
            start_time=100.0,
            finish_time=100.5,
            state="SUCCESS",
            retval={
                "status": "success",
                "provider_id": 1,
                "provider_name": "Recreation.gov",
                "search_name": "Tuolumne Meadows",
                "search_dates": "2026-08-01 → 2026-08-05",
            },
            kwargs={"target_id": "tgt-tuolumne"},
        )

        assert mock_redis.xadd.called
        _, record = mock_redis.xadd.call_args[0]
        assert record["task_name"] == "search.check-availability"
        assert record["provider_id"] == 1
        assert record["provider_name"] == "Recreation.gov"
        assert record["search_name"] == "Tuolumne Meadows"
        assert record["search_dates"] == "2026-08-01 → 2026-08-05"


def test_record_task_execution_failure_isolation() -> None:
    # Telemetry should never raise an exception even if Redis fails
    with patch(
        "worker.telemetry.get_redis_client", side_effect=ConnectionError("Redis down")
    ):
        # Should not raise
        record_task_execution(
            task_id="t-456",
            task_name="search.schedule-checks",
            worker="worker-1",
            start_time=50.0,
            finish_time=50.1,
            state="SUCCESS",
        )


def test_record_discovery_completion() -> None:
    mock_redis = MagicMock()
    with patch("worker.telemetry.get_redis_client", return_value=mock_redis):
        record_discovery_completion(
            targets_discovered=5,
            targets_enqueued=5,
            status="success",
        )

        assert mock_redis.setex.called
        key, ttl, value = mock_redis.setex.call_args[0]
        assert key == "camply:telemetry:discovery:last"
        assert '"targets_discovered": 5' in value
        assert '"status": "success"' in value


def test_retry_and_success_are_distinct_attempts_and_outcomes() -> None:
    """Retries share a Celery task ID while retaining separate history and metric events."""
    from worker import telemetry

    client = MagicMock()
    task = SimpleNamespace(
        name="synthetic.task", request=SimpleNamespace(hostname="worker-1", retries=0)
    )
    with (
        patch.object(telemetry, "get_redis_client", return_value=client),
        patch("worker.metrics.APPLICATION_OUTCOMES_TOTAL") as outcomes,
    ):
        for retry_count, state in enumerate(("RETRY", "SUCCESS")):
            task.request.retries = retry_count
            telemetry._on_telemetry_prerun(task_id="same-task")
            telemetry._on_telemetry_postrun(
                task=task,
                task_id="same-task",
                state=state,
                kwargs={"target_id": "synthetic-target"},
            )
    records = [call.args[1] for call in client.xadd.call_args_list]
    assert len(records) == 2
    assert records[0]["event_id"] != records[1]["event_id"]
    assert [record["attempt"] for record in records] == [1, 2]
    assert [record["outcome"] for record in records] == ["retrying", "success"]
    assert all(record["entity_id"] == "synthetic-target" for record in records)
    assert outcomes.labels.return_value.inc.call_count == 2


def test_retry_execution_is_not_a_celery_failure() -> None:
    """Execution counters preserve Celery's retry state rather than inflating failures."""
    from worker import metrics

    with patch.object(metrics, "CELERY_TASKS_TOTAL") as counter:
        metrics._on_task_postrun(
            task_id="synthetic-retry",
            task=SimpleNamespace(name="synthetic.task"),
            state="RETRY",
        )
    counter.labels.assert_called_once_with(task_name="synthetic.task", status="retry")
