"""Unit tests for ProgressStreamPublisher and Fenced Progress Emissions (Subsystem 5).

Verifies:
- Redis progress emission (XADD maxlen~1000, EXPIRE 86400s on terminal state)
- Fenced progress rule (terminal events omitted if DB fence returns 0 affected rows)
- Redis outage handling (Invariant 10: indexing succeeds even if Redis fails)
- Stream key and tail ID handling
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.progress_publisher import ProgressStreamPublisher, TERMINAL_TTL_SECONDS


@pytest.mark.asyncio
async def test_redis_progress_emission_non_terminal():
    """Verify XADD with MAXLEN~1000 and no EXPIRE for non-terminal progress."""
    mock_redis = AsyncMock()
    mock_redis.xadd.return_value = "1720000000000-0"

    publisher = ProgressStreamPublisher(async_client=mock_redis)
    gen_id = uuid4()
    payload = {"status": "parsing", "phase": "parsing", "files_processed": 50}

    msg_id = await publisher.publish_progress(gen_id, payload)

    assert msg_id == "1720000000000-0"
    mock_redis.xadd.assert_called_once()
    call_kwargs = mock_redis.xadd.call_args.kwargs
    assert call_kwargs["name"] == f"gitvane:progress:{gen_id}"
    assert call_kwargs["maxlen"] == 1000
    assert call_kwargs["approximate"] is True

    # Payload must be JSON serialized data field
    data_str = call_kwargs["fields"]["data"]
    parsed_data = json.loads(data_str)
    assert parsed_data["generation_id"] == str(gen_id)
    assert parsed_data["status"] == "parsing"

    # Non-terminal must NOT set EXPIRE
    mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_redis_progress_emission_terminal():
    """Verify XADD and EXPIRE 86400s when terminal state is reached."""
    mock_redis = AsyncMock()
    mock_redis.xadd.return_value = "1720000000000-1"

    publisher = ProgressStreamPublisher(async_client=mock_redis)
    gen_id = uuid4()
    payload = {"status": "completed", "phase": "completed", "progress_percentage": 100.0}

    msg_id = await publisher.publish_progress(gen_id, payload, is_terminal=True)

    assert msg_id == "1720000000000-1"
    mock_redis.xadd.assert_called_once()
    mock_redis.expire.assert_called_once_with(f"gitvane:progress:{gen_id}", TERMINAL_TTL_SECONDS)


@pytest.mark.asyncio
async def test_redis_outage_handling_invariant_10():
    """Verify Invariant 10: Redis outages do not crash or raise exceptions."""
    mock_redis = AsyncMock()
    mock_redis.xadd.side_effect = Exception("Redis connection refused")

    publisher = ProgressStreamPublisher(async_client=mock_redis)
    gen_id = uuid4()
    payload = {"status": "parsing"}

    # Must return None and log warning without raising exception
    msg_id = await publisher.publish_progress(gen_id, payload)
    assert msg_id is None


@pytest.mark.asyncio
async def test_get_tail_id():
    """Verify get_tail_id retrieves current stream head/tail entry or falls back to '0-0'."""
    mock_redis = AsyncMock()
    mock_redis.xrevrange.return_value = [("1720000000000-5", {"data": "{}"})]

    publisher = ProgressStreamPublisher(async_client=mock_redis)
    gen_id = uuid4()

    tail_id = await publisher.get_tail_id(gen_id)
    assert tail_id == "1720000000000-5"

    # Empty stream returns '0-0'
    mock_redis.xrevrange.return_value = []
    tail_id_empty = await publisher.get_tail_id(gen_id)
    assert tail_id_empty == "0-0"

    # Redis error returns '0-0'
    mock_redis.xrevrange.side_effect = Exception("Redis error")
    tail_id_err = await publisher.get_tail_id(gen_id)
    assert tail_id_err == "0-0"


@pytest.mark.asyncio
async def test_fenced_progress_rule_omitted_on_failed_fence():
    """Verify terminal progress is omitted if DB fence check affected 0 rows."""
    from app.execution.failure_engine import handle_parser_failure

    gen_id = uuid4()
    task_id = "stale-worker-task"

    mock_db = MagicMock()
    fence_res = MagicMock()
    fence_res.fetchone.return_value = None  # Fence check failed!
    mock_db.execute = AsyncMock(return_value=fence_res)

    with patch("app.services.progress_publisher.ProgressStreamPublisher.publish_progress") as mock_pub:
        result = await handle_parser_failure(
            db=mock_db,
            generation_id=gen_id,
            task_id=task_id,
            stage_attempt=1,
            error_message="Stale error",
        )

        assert result is None
        # Must NOT call terminal publish when fence check fails
        mock_pub.assert_not_called()


@pytest.mark.asyncio
async def test_fenced_progress_rule_emitted_on_successful_fence():
    """Verify terminal progress is emitted if DB fence check affected > 0 rows."""
    from app.execution.failure_engine import handle_parser_failure

    gen_id = uuid4()
    repo_id = uuid4()
    task_id = "valid-task"

    mock_db = MagicMock()
    fence_row = MagicMock()
    fence_row.repository_id = repo_id
    fence_res = MagicMock()
    fence_res.fetchone.return_value = fence_row

    desired_res = MagicMock()
    desired_res.scalar_one_or_none.return_value = gen_id  # Generation still desired

    upd_res = MagicMock()
    upd_res.rowcount = 1  # 1 row updated

    mock_db.execute = AsyncMock(side_effect=[fence_res, desired_res, upd_res])

    with patch("app.services.progress_publisher.ProgressStreamPublisher.publish_progress") as mock_pub:
        mock_pub.return_value = AsyncMock()
        result = await handle_parser_failure(
            db=mock_db,
            generation_id=gen_id,
            task_id=task_id,
            stage_attempt=1,
            error_message="Valid parser error",
        )

        assert result == "failed"
        # Must call terminal progress publish because fence update affected 1 row
        mock_pub.assert_called_once()
        kwargs = mock_pub.call_args.kwargs
        assert kwargs["generation_id"] == gen_id
        assert kwargs["payload"]["status"] == "failed"
        assert kwargs["is_terminal"] is True
