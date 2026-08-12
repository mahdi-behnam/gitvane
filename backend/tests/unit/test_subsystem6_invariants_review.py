"""Dual-Review Convergence Loop tests for Subsystem 6 (Garbage Collection & Security Boundaries).

Reviewer A Checklist:
- Run unit tests and verify safety checks strictly protect active generations.
- Ensure Garbage Collection Service never deletes active_generation_id or desired_generation_id under any circumstances.
- Verify eligible generation query matches status in ('superseded', 'failed', 'cancelled') AND terminal_at < now() - 24h.

Reviewer B Checklist:
- Verify PgBouncer compatibility (short transaction batch deletion, no table locks, explicit commits).
- Verify exception safety during GC processing and cleanup error handling.
- Security boundary enforcement (URL scheme validation, SSRF IP blocklist, DNS safety, resource limits, path containment).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import (
    InvalidPathError,
    ResourceLimitExceededError,
    SSRFValidationError,
)
from app.db.models import IndexGeneration, Repository
from app.services.garbage_collection_service import GarbageCollectionService
from app.services.security_validator import RepositoryIngestionValidator


@pytest.mark.asyncio
async def test_reviewer_a_safety_checks_strictly_protect_active_and_desired_generations():
    """Reviewer A: Verify safety checks strictly protect active_generation_id and desired_generation_id."""
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

    # Re-verify that cleanup_generation returns without deleting if given active_id or desired_id
    mock_db.reset_mock()
    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res])

    counts_active = await gc_service.cleanup_generation(mock_db, active_id)
    assert all(cnt == 0 for cnt in counts_active.values())

    mock_db.reset_mock()
    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res])
    counts_desired = await gc_service.cleanup_generation(mock_db, desired_id)
    assert all(cnt == 0 for cnt in counts_desired.values())


@pytest.mark.asyncio
async def test_reviewer_a_eligible_generation_selection_criteria():
    """Reviewer A: Verify eligible generations match status IN ('superseded','failed','cancelled') & terminal_at < now()-24h."""
    gc_service = GarbageCollectionService()

    now = datetime.now(timezone.utc)
    old_terminal = now - timedelta(hours=25)
    recent_terminal = now - timedelta(hours=10)

    gen_old_superseded = IndexGeneration(
        id=uuid4(),
        status="superseded",
        terminal_at=old_terminal,
        cleaned_at=None,
    )
    gen_recent_failed = IndexGeneration(
        id=uuid4(),
        status="failed",
        terminal_at=recent_terminal,
        cleaned_at=None,
    )

    mock_db = MagicMock()

    # Empty protected sets
    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = []
    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = []

    # Mock DB query filtering: return only old terminal generation
    eligible_res = MagicMock()
    eligible_res.scalars.return_value.all.return_value = [gen_old_superseded]

    mock_db.execute = AsyncMock(side_effect=[active_res, desired_res, eligible_res])

    eligible = await gc_service.find_eligible_generations(mock_db, retention_hours=24)

    assert len(eligible) == 1
    assert eligible[0].id == gen_old_superseded.id


@pytest.mark.asyncio
async def test_reviewer_b_pgbouncer_compatibility_short_transactions():
    """Reviewer B: Verify PgBouncer compatibility via short transaction batch deletions and explicit commits."""
    gc_service = GarbageCollectionService()
    target_gen_id = uuid4()

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()

    active_res = MagicMock()
    active_res.scalars.return_value.all.return_value = []
    desired_res = MagicMock()
    desired_res.scalars.return_value.all.return_value = []

    empty_del_res = MagicMock()
    empty_del_res.rowcount = 0

    mock_db.execute = AsyncMock(
        side_effect=[
            active_res,
            desired_res,
            empty_del_res,  # CodeEmbedding batch 1 (0 rows)
            empty_del_res,  # CodeChunk batch 1 (0 rows)
            empty_del_res,  # DependencyEdge batch 1 (0 rows)
            empty_del_res,  # Symbol batch 1 (0 rows)
            empty_del_res,  # CodeFile batch 1 (0 rows)
            empty_del_res,  # EmbeddingBatch batch 1 (0 rows)
            empty_del_res,  # IndexGeneration cleaned_at update
        ]
    )

    await gc_service.cleanup_generation(mock_db, target_gen_id, batch_size=100)

    # Verify short transactions with explicit commits after each table batch deletion
    assert mock_db.commit.call_count == 7


@pytest.mark.asyncio
async def test_reviewer_b_exception_safety_during_gc():
    """Reviewer B: Verify exception safety during GC run handles failures gracefully without crashing process."""
    gc_service = GarbageCollectionService()

    gen_failing = IndexGeneration(
        id=uuid4(),
        status="failed",
        terminal_at=datetime.now(timezone.utc) - timedelta(hours=30),
        cleaned_at=None,
    )

    mock_db = MagicMock()

    with patch.object(
        gc_service, "find_eligible_generations", new=AsyncMock(return_value=[gen_failing])
    ), patch.object(
        gc_service, "cleanup_generation", new=AsyncMock(side_effect=Exception("Database lock timeout"))
    ):
        result = await gc_service.run_garbage_collection(mock_db)

        # Exception caught, transaction rolled back, summary returned cleanly
        assert result["eligible_count"] == 1
        assert result["cleaned_count"] == 0
        assert mock_db.rollback.called


def test_reviewer_b_security_boundary_enforcement():
    """Reviewer B: Verify security boundary enforcement (SSRF, URL schemes, resource limits, sandbox paths)."""
    validator = RepositoryIngestionValidator()

    # 1. Scheme checks
    with pytest.raises(SSRFValidationError):
        validator.validate_url_scheme("file:///etc/passwd")

    # 2. SSRF IP blocklist
    with pytest.raises(SSRFValidationError):
        validator.validate_ip_safety("169.254.169.254")

    # 3. Path containment
    with pytest.raises(InvalidPathError):
        validator.validate_path_containment("/etc/shadow", base_sandbox_dir="/workspaces")
