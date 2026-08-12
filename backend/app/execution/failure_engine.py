"""Task-specific failure fencing logic for Subsystem 2.

Section 14: Task-Specific Failure Fencing
- Parser terminal failure handler (verifies stage lease owner, attempt, expiry before transitioning to failed or superseded)
- Embedding batch terminal failure handler (fenced batch update processing -> failed first, then transitions generation to failed or superseded if desired)
- Stale workers are fenced out and prevented from committing terminal failures
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmbeddingBatch, IndexGeneration, Repository


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def handle_parser_failure(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    stage_attempt: int,
    error_message: str,
) -> Optional[str]:
    """Handle parser task terminal failure under stage lease fence.
    
    Returns 'failed', 'superseded', or None if fence check failed.
    """
    now_utc = get_utc_now()

    # Verify parser stage fence
    fence_stmt = select(IndexGeneration.id, IndexGeneration.repository_id).where(
        IndexGeneration.id == generation_id,
        IndexGeneration.stage_lease_owner == task_id,
        IndexGeneration.stage_attempt == stage_attempt,
        IndexGeneration.stage_lease_expires_at > now_utc,
        IndexGeneration.status.in_(["preparing", "parsing"]),
    )
    res = await db.execute(fence_stmt)
    row = res.fetchone()
    if not row:
        return None  # Fence check failed, ignore stale worker

    repo_id = row.repository_id

    # Check if generation is still desired
    repo_stmt = select(Repository.desired_generation_id).where(Repository.id == repo_id)
    repo_res = await db.execute(repo_stmt)
    desired_gen_id = repo_res.scalar_one_or_none()

    target_status = "failed" if desired_gen_id == generation_id else "superseded"

    stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.stage_lease_owner == task_id,
            IndexGeneration.stage_attempt == stage_attempt,
            IndexGeneration.status.in_(["preparing", "parsing"]),
        )
        .values(
            status=target_status,
            error_message=error_message,
            terminal_at=now_utc,
            stage_lease_owner=None,
            stage_lease_expires_at=None,
            updated_at=now_utc,
        )
    )
    upd_res = await db.execute(stmt)
    if upd_res.rowcount > 0:
        from app.services.progress_publisher import ProgressStreamPublisher
        publisher = ProgressStreamPublisher()
        await publisher.publish_progress(
            generation_id=generation_id,
            payload={
                "status": target_status,
                "phase": target_status,
                "phase_name": f"Indexing {target_status}",
                "error": error_message,
            },
            is_terminal=True,
        )
        return target_status
    return None


async def handle_embedding_batch_failure(
    db: AsyncSession,
    generation_id: UUID,
    batch_index: int,
    task_id: str,
    error_message: str,
) -> Optional[str]:
    """Handle embedding batch task terminal failure under batch lease fence.
    
    1. Fenced batch update: processing -> failed.
    2. Only if batch update succeeds, check desired generation and transition generation embedding -> failed (or superseded).
    Returns 'failed', 'superseded', or None if fence check failed.
    """
    now_utc = get_utc_now()

    # 1. Fenced batch update
    batch_stmt = (
        update(EmbeddingBatch)
        .where(
            EmbeddingBatch.generation_id == generation_id,
            EmbeddingBatch.batch_index == batch_index,
            EmbeddingBatch.status == "processing",
            EmbeddingBatch.lease_owner == task_id,
            EmbeddingBatch.lease_expires_at > now_utc,
        )
        .values(
            status="failed",
            last_error=error_message,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    batch_res = await db.execute(batch_stmt)
    if batch_res.rowcount == 0:
        return None  # Stale worker, fence failed

    # 2. Transition generation if currently embedding
    gen_stmt = select(IndexGeneration.repository_id, IndexGeneration.status).where(
        IndexGeneration.id == generation_id
    )
    gen_res = await db.execute(gen_stmt)
    gen_row = gen_res.fetchone()
    if not gen_row or gen_row.status != "embedding":
        return None

    repo_id = gen_row.repository_id
    repo_stmt = select(Repository.desired_generation_id).where(Repository.id == repo_id)
    repo_res = await db.execute(repo_stmt)
    desired_gen_id = repo_res.scalar_one_or_none()

    target_status = "failed" if desired_gen_id == generation_id else "superseded"

    upd_gen_stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.status == "embedding",
        )
        .values(
            status=target_status,
            error_message=f"Embedding batch {batch_index} failed: {error_message}",
            terminal_at=now_utc,
            updated_at=now_utc,
        )
    )
    upd_res = await db.execute(upd_gen_stmt)
    if upd_res.rowcount > 0:
        from app.services.progress_publisher import ProgressStreamPublisher
        publisher = ProgressStreamPublisher()
        await publisher.publish_progress(
            generation_id=generation_id,
            payload={
                "status": target_status,
                "phase": target_status,
                "phase_name": f"Indexing {target_status}",
                "error": f"Embedding batch {batch_index} failed: {error_message}",
            },
            is_terminal=True,
        )
        return target_status
    return None

