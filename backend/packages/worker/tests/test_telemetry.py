"""
Tests for worker task telemetry and discovery completion metadata.
"""

from unittest.mock import MagicMock, patch

from celery.exceptions import Retry

from worker.telemetry import (
    _extract_entity_info,
    _normalize_outcome,
    record_discovery_completion,
    record_task_execution,
)


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
            task_name="worker.tasks.scanner.check_target_availability",
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


def test_record_task_execution_failure_isolation() -> None:
    # Telemetry should never raise an exception even if Redis fails
    with patch(
        "worker.telemetry.get_redis_client", side_effect=ConnectionError("Redis down")
    ):
        # Should not raise
        record_task_execution(
            task_id="t-456",
            task_name="worker.tasks.heartbeat.discover_targets",
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
