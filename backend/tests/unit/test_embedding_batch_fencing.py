"""Unit tests for Embedding Batch Task & Batch Lease Fencing (Section 12)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.execution.embedding_engine import (
    checkpoint_batch_completion,
    claim_embedding_batch_lease,
    persist_batch_embeddings,
    verify_embedding_batch_fence,
)


@pytest.mark.asyncio
async def test_claim_embedding_batch_lease_success():
    gen_id = uuid4()
    batch_id = uuid4()
    task_id = "task-embed-001"

    db = MagicMock()
    # Mock backend query
    backend_res = MagicMock()
    backend_res.scalar_one_or_none.return_value = "local"

    # Mock update returning batch row
    batch_row = MagicMock()
    batch_row.id = batch_id
    batch_row.generation_id = gen_id
    batch_row.batch_index = 0
    batch_row.chunk_start_id = 1
    batch_row.chunk_end_id = 16
    batch_row.attempt_count = 1
    update_res = MagicMock()
    update_res.fetchone.return_value = batch_row

    # Mock gen details query
    gen_row = MagicMock()
    gen_row.embedding_backend = "local"
    gen_row.embedding_model = "jina"
    gen_row.embedding_dimension = 768
    gen_row.embedding_config_hash = "hash123"
    gen_res = MagicMock()
    gen_res.fetchone.return_value = gen_row

    db.execute = AsyncMock(side_effect=[backend_res, update_res, gen_res])

    result = await claim_embedding_batch_lease(db, gen_id, 0, task_id)

    assert result is not None
    assert result["batch_id"] == batch_id
    assert result["batch_index"] == 0
    assert result["attempt_count"] == 1


@pytest.mark.asyncio
async def test_persist_batch_embeddings_fence_failure():
    gen_id = uuid4()
    task_id = "stale-worker"

    db = MagicMock()
    fence_res = MagicMock()
    fence_res.scalar_one_or_none.return_value = None  # Fence lost
    db.execute = AsyncMock(return_value=fence_res)

    embeddings = [{"chunk_id": 1, "provider": "local", "model": "m", "dimensions": 768, "embedding": [0.1] * 768}]
    success = await persist_batch_embeddings(db, gen_id, 0, task_id, embeddings)

    assert success is False


@pytest.mark.asyncio
async def test_checkpoint_batch_completion_intermediate_batch():
    gen_id = uuid4()
    task_id = "task-embed-002"

    db = MagicMock()
    update_res = MagicMock()
    update_res.rowcount = 1

    rem_res = MagicMock()
    rem_res.scalar.return_value = 2  # 2 batches remain non-completed

    db.execute = AsyncMock(side_effect=[update_res, rem_res])

    res = await checkpoint_batch_completion(db, gen_id, 0, task_id)

    assert res["completed"] is True
    assert res["finalized"] is False


@pytest.mark.asyncio
async def test_checkpoint_batch_completion_last_batch_triggers_finalizing():
    gen_id = uuid4()
    task_id = "task-embed-003"

    db = MagicMock()
    update_res = MagicMock()
    update_res.rowcount = 1

    rem_res = MagicMock()
    rem_res.scalar.return_value = 0  # 0 batches remain!

    gen_res = MagicMock()
    gen_res.rowcount = 1

    db.execute = AsyncMock(side_effect=[update_res, rem_res, gen_res])
    db.add = MagicMock()

    res = await checkpoint_batch_completion(db, gen_id, 0, task_id)

    assert res["completed"] is True
    assert res["finalized"] is True
    assert db.add.call_count == 1  # activation_requested OutboxEvent added
