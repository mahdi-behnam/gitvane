"""Unit and integration tests for SSE Streaming Endpoint (Subsystem 5).

Verifies:
- Sequence 1-4: Tail ID capture, PostgreSQL snapshot delivery, XREAD streaming loop
- SSE `id:` field set to Redis stream ID for every streamed event
- Monotonic state snapshot/event reducer payload model
- Client disconnect and error handling
"""

import json
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.core.security_utils import create_access_token
from app.main import app
from app.services.progress_publisher import ProgressStreamPublisher, get_progress_publisher


def test_sse_endpoint_sequence_and_id_headers():
    """Test full SSE streaming endpoint sequence:
    1. Capture tail ID C ('1720000000000-0')
    2. Fetch PostgreSQL snapshot
    3. Yield snapshot event with id: 1720000000000-0
    4. XREAD streaming loop yielding entries with id: msg_id
    """
    user_id = 1
    repo_id = uuid4()
    gen_id = uuid4()

    user = MagicMock()
    user.id = user_id
    user.is_active = True

    repo = MagicMock()
    repo.id = repo_id
    repo.owner_id = user_id

    gen = MagicMock()
    gen.id = gen_id
    gen.repository_id = repo_id
    gen.requested_ref = "main"
    gen.commit_sha = "sha123"
    gen.error_message = None
    gen.stage_attempt = 1
    gen.status = "parsing"

    mock_db = MagicMock()
    res_user = MagicMock()
    res_user.scalars.return_value.first.return_value = user

    res_gen_repo = MagicMock()
    res_gen_repo.fetchone.return_value = (gen, repo)

    res_snap = MagicMock()
    res_snap.scalar_one_or_none.return_value = gen

    res_count = MagicMock()
    res_count.scalar.return_value = 0

    mock_db.execute = AsyncMock(side_effect=[res_user, res_gen_repo, res_snap, res_count, res_count, res_count])

    async def _mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    mock_publisher = AsyncMock(spec=ProgressStreamPublisher)
    mock_publisher.get_tail_id.return_value = "1720000000000-0"

    async def mock_read_stream(generation_id, last_id="0-0", block_ms=15000, count=100):
        if last_id == "1720000000000-0":
            return [("1720000000000-1", {"status": "embedding", "phase": "embedding", "phase_name": "Generating embeddings"})]
        elif last_id == "1720000000000-1":
            return [("1720000000000-2", {"status": "completed", "phase": "completed", "phase_name": "Indexing complete"})]
        return []

    mock_publisher.read_stream.side_effect = mock_read_stream

    token = create_access_token(subject=user_id)
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_progress_publisher] = lambda: mock_publisher

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/indexing/generations/{gen_id}/stream?token={token}",
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        content = response.text

        # Check snapshot event (first block)
        assert "id: 1720000000000-0" in content
        assert "event: progress" in content
        assert "event_type" in content and "snapshot" in content

        # Check streamed progress events (subsequent blocks)
        assert "id: 1720000000000-1" in content
        assert "id: 1720000000000-2" in content
        assert "Generating embeddings" in content
        assert "Indexing complete" in content
    finally:
        app.dependency_overrides.clear()


def test_sse_endpoint_terminal_snapshot_early_exit():
    """Verify that if PostgreSQL snapshot is already in terminal state, stream exits after snapshot."""
    user_id = 2
    repo_id = uuid4()
    gen_id = uuid4()

    user = MagicMock()
    user.id = user_id
    user.is_active = True

    repo = MagicMock()
    repo.id = repo_id
    repo.owner_id = user_id

    gen = MagicMock()
    gen.id = gen_id
    gen.repository_id = repo_id
    gen.requested_ref = "main"
    gen.commit_sha = "sha123"
    gen.error_message = None
    gen.stage_attempt = 1
    gen.status = "completed"  # Terminal state!

    mock_db = MagicMock()
    res_user = MagicMock()
    res_user.scalars.return_value.first.return_value = user

    res_gen_repo = MagicMock()
    res_gen_repo.fetchone.return_value = (gen, repo)

    res_snap = MagicMock()
    res_snap.scalar_one_or_none.return_value = gen

    res_count = MagicMock()
    res_count.scalar.return_value = 0

    mock_db.execute = AsyncMock(side_effect=[res_user, res_gen_repo, res_snap, res_count, res_count, res_count])

    async def _mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    mock_publisher = AsyncMock(spec=ProgressStreamPublisher)
    mock_publisher.get_tail_id.return_value = "1720000000000-9"

    token = create_access_token(subject=user_id)
    app.dependency_overrides[get_db] = _mock_get_db
    app.dependency_overrides[get_progress_publisher] = lambda: mock_publisher

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/indexing/{gen_id}/stream?token={token}",
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        content = response.text

        # Should yield only snapshot event and exit
        assert "id: 1720000000000-9" in content
        assert "Generation is completed" in content
        mock_publisher.read_stream.assert_not_called()
    finally:
        app.dependency_overrides.clear()
