"""Unit tests for Parser Task and Stage Lease Fencing."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.execution.parser_engine import (
    FenceCheckFailedError,
    claim_parser_stage_lease,
    cleanup_incomplete_staged_rows,
    final_parser_checkpoint,
    get_ephemeral_workspace_path,
    resolve_and_freeze_commit_sha,
    transition_preparing_to_parsing,
    verify_parser_fence,
)


@pytest.mark.asyncio
async def test_ephemeral_workspace_path_structure():
    gen_id = uuid4()
    sha = "a1b2c3d4e5f67890123456789012345678901234"
    path = get_ephemeral_workspace_path(gen_id, sha)

    assert str(gen_id) in str(path)
    assert sha in str(path)
    assert "workspaces" in str(path)


@pytest.mark.asyncio
async def test_claim_parser_stage_lease_successful():
    gen_id = uuid4()
    repo_id = uuid4()
    task_id = "task-parser-001"

    db = MagicMock()
    mock_row = MagicMock()
    mock_row.id = gen_id
    mock_row.repository_id = repo_id
    mock_row.requested_ref = "main"
    mock_row.commit_sha = None
    mock_row.stage_attempt = 1
    mock_row.pipeline_version = "v1"
    mock_row.parser_version = "v1"
    mock_row.chunker_version = "v1"
    mock_row.embedding_backend = "local"
    mock_row.embedding_model = "jina"
    mock_row.embedding_dimension = 768
    mock_row.embedding_config_hash = "hash123"

    mock_res = MagicMock()
    mock_res.fetchone.return_value = mock_row
    db.execute = AsyncMock(return_value=mock_res)

    result = await claim_parser_stage_lease(db, gen_id, task_id)

    assert result is not None
    assert result["id"] == gen_id
    assert result["stage_attempt"] == 1
    assert result["requested_ref"] == "main"


@pytest.mark.asyncio
async def test_claim_parser_stage_lease_returns_none_when_not_desired():
    gen_id = uuid4()
    task_id = "task-parser-002"

    db = MagicMock()
    mock_res = MagicMock()
    mock_res.fetchone.return_value = None
    db.execute = AsyncMock(return_value=mock_res)

    result = await claim_parser_stage_lease(db, gen_id, task_id)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_and_freeze_commit_sha_reuses_existing():
    gen_id = uuid4()
    task_id = "task-parser-003"
    existing_sha = "1234567890abcdef1234567890abcdef12345678"

    db = MagicMock()
    git_svc = MagicMock()

    resolved = await resolve_and_freeze_commit_sha(
        db=db,
        generation_id=gen_id,
        task_id=task_id,
        claimed_attempt=1,
        git_service=git_svc,
        repo_path=MagicMock(),
        requested_ref="main",
        current_commit_sha=existing_sha,
    )

    assert resolved == existing_sha
    git_svc.resolve_ref_to_sha.assert_not_called()


@pytest.mark.asyncio
async def test_final_parser_checkpoint_n_greater_than_zero():
    gen_id = uuid4()
    task_id = "task-parser-004"

    db = MagicMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = gen_id
    db.execute = AsyncMock(return_value=mock_res)
    db.add_all = MagicMock()

    chunks = [MagicMock(id=i) for i in range(1, 35)]  # 35 chunks => 3 batches of 16

    result = await final_parser_checkpoint(
        db=db,
        generation_id=gen_id,
        task_id=task_id,
        claimed_attempt=1,
        chunks=chunks,
        embedding_backend="local",
        batch_size=16,
    )

    assert result["next_status"] == "embedding"
    assert result["num_batches"] == 3
    assert db.add_all.call_count == 2  # batch_rows and outbox_events


@pytest.mark.asyncio
async def test_final_parser_checkpoint_n_zero():
    gen_id = uuid4()
    task_id = "task-parser-005"

    db = MagicMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = gen_id
    db.execute = AsyncMock(return_value=mock_res)
    db.add = MagicMock()

    result = await final_parser_checkpoint(
        db=db,
        generation_id=gen_id,
        task_id=task_id,
        claimed_attempt=1,
        chunks=[],
        embedding_backend="local",
    )

    assert result["next_status"] == "finalizing"
    assert result["num_batches"] == 0
    assert db.add.call_count == 1  # single activation_requested OutboxEvent
