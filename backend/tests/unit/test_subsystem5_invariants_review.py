"""Dual-Review Convergence Loop tests for Subsystem 5 (Progress Stream & SSE).

Reviewer A Checklist:
- Invariant 2 (PostgreSQL owns workflow truth): PostgreSQL remains authoritative; Redis outages do not corrupt DB generation status or workflow state.
- Invariant 7 (State transitions are monotonic): Terminal states set 24h key TTL; terminal generations never return to active state.
- Invariant 10 (Redis progress is ephemeral): Redis operation failures allow indexing tasks to complete cleanly.

Reviewer B Checklist:
- Async SSE streaming resource management: Request disconnect checking, graceful generator exit.
- Redis client connection pooling: Connection pooling, shared client reuse, clean close().
- Exception handling: Exception safety in publisher and stream endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models import IndexGeneration, Repository
from app.services.progress_publisher import ProgressStreamPublisher


@pytest.mark.asyncio
async def test_reviewer_a_invariant_2_and_10_redis_outage_does_not_corrupt_db():
    """Reviewer A: Verify Invariant 2 & 10 hold when Redis is offline."""
    from app.execution.activation_engine import activate_generation

    repo_id = uuid4()
    gen_id = uuid4()

    gen = MagicMock()
    gen.id = gen_id
    gen.repository_id = repo_id
    gen.status = "finalizing"

    repo = MagicMock()
    repo.id = repo_id
    repo.desired_generation_id = gen_id
    repo.active_generation_id = None

    mock_db = MagicMock()
    gen_res = MagicMock()
    gen_res.scalar_one_or_none.return_value = gen

    repo_res = MagicMock()
    repo_res.scalar_one_or_none.return_value = repo

    mock_db.execute = AsyncMock(side_effect=[None, None, gen_res, repo_res])

    # Simulate Redis total outage during progress stream publication
    with patch("redis.asyncio.Redis.xadd", side_effect=Exception("Redis Server Unavailable")):
        res = await activate_generation(mock_db, gen_id)

        # Invariant 2 & 10: DB activation MUST succeed despite Redis outage
        assert res["status"] == "completed"
        assert repo.active_generation_id == gen_id
        assert gen.status == "completed"


@pytest.mark.asyncio
async def test_reviewer_a_invariant_7_terminal_ttl():
    """Reviewer A: Verify Invariant 7 - terminal state sets 24h key TTL."""
    mock_redis = AsyncMock()
    publisher = ProgressStreamPublisher(async_client=mock_redis)

    gen_id = uuid4()
    for terminal_status in ["completed", "failed", "cancelled", "superseded"]:
        mock_redis.reset_mock()
        await publisher.publish_progress(gen_id, {"status": terminal_status})
        mock_redis.expire.assert_called_once_with(f"gitvane:progress:{gen_id}", 86400)


@pytest.mark.asyncio
async def test_reviewer_b_redis_connection_pooling_and_close():
    """Reviewer B: Verify Redis client connection pooling reuse and close()."""
    ProgressStreamPublisher._async_redis_client = None
    ProgressStreamPublisher._sync_redis_client = None

    publisher = ProgressStreamPublisher()

    client1 = publisher.get_async_client()
    client2 = publisher.get_async_client()

    # Reuses same client instance (connection pool)
    assert client1 is client2

    sync1 = publisher.get_sync_client()
    sync2 = publisher.get_sync_client()
    assert sync1 is sync2

    # Clean close
    await ProgressStreamPublisher.close()
    assert ProgressStreamPublisher._async_redis_client is None
    assert ProgressStreamPublisher._sync_redis_client is None


@pytest.mark.asyncio
async def test_reviewer_b_sse_stream_exception_handling():
    """Reviewer B: Verify SSE stream handles exceptions gracefully without server crash."""
    mock_redis = AsyncMock()
    mock_redis.xrevrange.side_effect = Exception("Connection reset by peer")

    publisher = ProgressStreamPublisher(async_client=mock_redis)
    gen_id = uuid4()

    # Calling get_tail_id failure gracefully falls back to '0-0' without raising exception
    tail_id = await publisher.get_tail_id(gen_id)
    assert tail_id == "0-0"
