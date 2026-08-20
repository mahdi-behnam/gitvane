"""Unit tests for Task-Specific Failure Fencing."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.execution.failure_engine import (
    handle_embedding_batch_failure,
    handle_parser_failure,
)


@pytest.mark.asyncio
async def test_handle_parser_failure_fence_failure_ignores_stale_worker():
    gen_id = uuid4()
    task_id = "stale-parser"

    db = MagicMock()
    mock_res = MagicMock()
    mock_res.fetchone.return_value = None  # Fence check failed
    db.execute = AsyncMock(return_value=mock_res)

    status = await handle_parser_failure(db, gen_id, task_id, 1, "Parse error")
    assert status is None


@pytest.mark.asyncio
async def test_handle_parser_failure_desired_generation_fails():
    gen_id = uuid4()
    repo_id = uuid4()
    task_id = "valid-parser"

    db = MagicMock()
    fence_row = MagicMock()
    fence_row.repository_id = repo_id
    fence_res = MagicMock()
    fence_res.fetchone.return_value = fence_row

    desired_res = MagicMock()
    desired_res.scalar_one_or_none.return_value = gen_id  # Generation is still desired!

    upd_res = MagicMock()
    upd_res.rowcount = 1

    db.execute = AsyncMock(side_effect=[fence_res, desired_res, upd_res])

    status = await handle_parser_failure(db, gen_id, task_id, 1, "SyntaxError")
    assert status == "failed"


@pytest.mark.asyncio
async def test_handle_parser_failure_superseded_generation():
    gen_id = uuid4()
    repo_id = uuid4()
    new_gen_id = uuid4()
    task_id = "old-parser"

    db = MagicMock()
    fence_row = MagicMock()
    fence_row.repository_id = repo_id
    fence_res = MagicMock()
    fence_res.fetchone.return_value = fence_row

    desired_res = MagicMock()
    desired_res.scalar_one_or_none.return_value = new_gen_id  # Desired generation has changed!

    upd_res = MagicMock()
    upd_res.rowcount = 1

    db.execute = AsyncMock(side_effect=[fence_res, desired_res, upd_res])

    status = await handle_parser_failure(db, gen_id, task_id, 1, "Parse error")
    assert status == "superseded"


@pytest.mark.asyncio
async def test_handle_embedding_batch_failure_stale_worker():
    gen_id = uuid4()
    task_id = "stale-embedder"

    db = MagicMock()
    batch_res = MagicMock()
    batch_res.rowcount = 0  # Batch lease fence failed
    db.execute = AsyncMock(return_value=batch_res)

    status = await handle_embedding_batch_failure(db, gen_id, 0, task_id, "CUDA OOM")
    assert status is None


@pytest.mark.asyncio
async def test_handle_embedding_batch_failure_desired_fails():
    gen_id = uuid4()
    repo_id = uuid4()
    task_id = "valid-embedder"

    db = MagicMock()
    batch_res = MagicMock()
    batch_res.rowcount = 1  # Batch updated to failed

    gen_row = MagicMock()
    gen_row.repository_id = repo_id
    gen_row.status = "embedding"
    gen_res = MagicMock()
    gen_res.fetchone.return_value = gen_row

    desired_res = MagicMock()
    desired_res.scalar_one_or_none.return_value = gen_id  # Generation is still desired!

    upd_res = MagicMock()
    upd_res.rowcount = 1

    db.execute = AsyncMock(side_effect=[batch_res, gen_res, desired_res, upd_res])

    status = await handle_embedding_batch_failure(db, gen_id, 0, task_id, "CUDA OOM")
    assert status == "failed"
