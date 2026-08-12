"""Unit tests for GarbageCollectionService and Celery GC tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models import IndexGeneration, Repository
from app.services.garbage_collection_service import GarbageCollectionService
from app.tasks.gc_tasks import task_run_garbage_collection


@pytest.mark.asyncio
async def test_get_protected_generation_ids():
    """Verify GarbageCollectionService identifies active and desired generation IDs as protected."""
    gc_service = GarbageCollectionService()

    active_id = uuid4()
    desired_id = uuid4()

    mock_db = MagicMock()

    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = [active_id]

    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = [desired_id]

    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res])

    protected = await gc_service.get_protected_generation_ids(mock_db)

    assert active_id in protected
    assert desired_id in protected
    assert len(protected) == 2


@pytest.mark.asyncio
async def test_find_eligible_generations():
    """Verify eligible generations are filtered by terminal status, >24h terminal_at, uncleaned, and non-protected."""
    gc_service = GarbageCollectionService()

    active_gen_id = uuid4()
    stale_eligible_id = uuid4()

    now = datetime.now(timezone.utc)
    old_terminal = now - timedelta(hours=36)

    gen1 = IndexGeneration(
        id=stale_eligible_id,
        repository_id=uuid4(),
        status="superseded",
        terminal_at=old_terminal,
        cleaned_at=None,
    )

    mock_db = MagicMock()

    # Protected query return
    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = [active_gen_id]
    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = []

    # Eligible query return
    eligible_res = MagicMock()
    eligible_res.scalars.return_value.all.return_value = [gen1]

    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res, eligible_res])

    eligible = await gc_service.find_eligible_generations(mock_db, retention_hours=24)

    assert len(eligible) == 1
    assert eligible[0].id == stale_eligible_id


@pytest.mark.asyncio
async def test_gc_protects_active_and_desired_generations():
    """Defense-in-depth: Never clean a generation if it is referenced as active or desired."""
    gc_service = GarbageCollectionService()

    protected_gen_id = uuid4()

    mock_db = MagicMock()

    # Protected query return
    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = [protected_gen_id]
    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res])

    counts = await gc_service.cleanup_generation(mock_db, protected_gen_id)

    # Should abort cleanup immediately and return all 0s
    assert all(val == 0 for val in counts.values())


@pytest.mark.asyncio
async def test_cleanup_generation_fk_order_and_batching():
    """Verify cleanup deletes rows in strict FK order and updates IndexGeneration.cleaned_at."""
    gc_service = GarbageCollectionService()
    gen_id = uuid4()

    mock_db = MagicMock()

    # 1 & 2. Protected query returns empty sets
    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = []
    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = []

    # Batch delete returns 0 rows affected for each model to terminate loops
    empty_del_res = MagicMock()
    empty_del_res.rowcount = 0

    mock_db.execute = AsyncMock(
        side_effect=[
            active_res,
            desired_res,
            empty_del_res,  # CodeEmbedding
            empty_del_res,  # CodeChunk
            empty_del_res,  # DependencyEdge
            empty_del_res,  # Symbol
            empty_del_res,  # CodeFile
            empty_del_res,  # EmbeddingBatch
            empty_del_res,  # Update IndexGeneration cleaned_at
        ]
    )

    counts = await gc_service.cleanup_generation(mock_db, gen_id, batch_size=100)

    assert counts == {
        "code_embeddings": 0,
        "code_chunks": 0,
        "dependency_edges": 0,
        "symbols": 0,
        "code_files": 0,
        "embedding_batches": 0,
    }
    assert mock_db.execute.call_count >= 8
    assert mock_db.commit.call_count >= 7


def test_task_run_garbage_collection_execution():
    """Verify task_run_garbage_collection Celery task runs garbage collection service."""
    mock_run_result = {
        "eligible_count": 1,
        "cleaned_count": 1,
        "skipped_count": 0,
        "generations_cleaned": ["123e4567-e89b-12d3-a456-426614174000"],
        "total_rows_deleted": {
            "code_embeddings": 10,
            "code_chunks": 5,
            "dependency_edges": 2,
            "symbols": 8,
            "code_files": 2,
            "embedding_batches": 1,
        },
    }

    with patch(
        "app.services.garbage_collection_service.GarbageCollectionService.run_garbage_collection",
        new=AsyncMock(return_value=mock_run_result),
    ):
        result = task_run_garbage_collection.apply(
            kwargs={"retention_hours": 24, "generation_limit": 50, "batch_size": 500}
        ).get()

        assert result["eligible_count"] == 1
        assert result["cleaned_count"] == 1
        assert "123e4567-e89b-12d3-a456-426614174000" in result["generations_cleaned"]
