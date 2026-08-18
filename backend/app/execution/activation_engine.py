"""Activation Engine for GitVane execution pipeline (Section 13).

Handles atomic generation activation under lock timeouts and monotonic state transitions.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IndexGeneration, Repository

logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


async def activate_generation(
    db: AsyncSession,
    generation_id: UUID,
) -> dict[str, Any]:
    """Atomically activate an IndexGeneration if finalizing and still desired.
    
    1. Lock Repository and IndexGeneration in one transaction.
    2. Enforce monotonic state transitions and desired generation fencing.
    3. Update active_generation_id and mark previous active generation superseded.
    """
    now_utc = get_utc_now()

    # Try setting local lock and statement timeouts (PostgreSQL specific)
    try:
        await db.execute(text("SET LOCAL lock_timeout = '3s';"))
        await db.execute(text("SET LOCAL statement_timeout = '5s';"))
    except Exception:
        # Pass gracefully on SQLite / test dialects
        pass

    # 1. Fetch generation row with lock
    gen_stmt = (
        select(IndexGeneration)
        .where(IndexGeneration.id == generation_id)
        .with_for_update()
    )
    gen_res = await db.execute(gen_stmt)
    gen = gen_res.scalar_one_or_none()

    if not gen:
        return {"status": "error", "reason": "generation_not_found"}

    # 2. Fetch parent repository with lock
    repo_stmt = (
        select(Repository)
        .where(Repository.id == gen.repository_id)
        .with_for_update()
    )
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()

    if not repo:
        return {"status": "error", "reason": "repository_not_found"}

    # Case 1: Already active & completed
    if gen.status == "completed" and repo.active_generation_id == gen.id:
        return {"status": "already_active", "generation_id": str(gen.id)}

    # Case 2: Terminal generation
    if gen.status in ("failed", "cancelled", "superseded"):
        return {"status": "skipped", "reason": f"generation_is_{gen.status}"}

    # Case 3: Not in finalizing state
    if gen.status != "finalizing":
        return {"status": "skipped", "reason": f"generation_status_{gen.status}_not_finalizing"}

    # Case 4: No longer desired generation -> mark superseded
    if repo.desired_generation_id != gen.id:
        gen.status = "superseded"
        gen.terminal_at = now_utc
        gen.updated_at = now_utc

        from app.services.progress_publisher import ProgressStreamPublisher
        publisher = ProgressStreamPublisher()
        await publisher.publish_progress(
            generation_id=gen.id,
            payload={
                "status": "superseded",
                "phase": "superseded",
                "phase_name": "Indexing superseded",
            },
            is_terminal=True,
        )
        return {"status": "superseded", "reason": "generation_fenced_by_newer_desired"}

    # Case 5: Finalizing & desired -> Activate!
    previous_active_id = repo.active_generation_id

    repo.active_generation_id = gen.id
    repo.status = "indexed"
    repo.indexed_at = now_utc
    if gen.requested_ref:
        repo.current_ref = gen.requested_ref
    if gen.commit_sha:
        repo.last_indexed_commit = gen.commit_sha

    gen.status = "completed"
    gen.completed_at = now_utc
    gen.terminal_at = now_utc
    gen.updated_at = now_utc

    total_files = 0
    total_chunks = 0
    try:
        from sqlalchemy import func
        from app.db.models import CodeChunk, CodeFile
        total_files_stmt = select(func.count(CodeFile.id)).where(CodeFile.generation_id == gen.id)
        total_files_res = await db.execute(total_files_stmt)
        if total_files_res is not None and hasattr(total_files_res, "scalar"):
            tf_val = total_files_res.scalar()
            total_files = int(tf_val) if tf_val is not None else 0

        total_chunks_stmt = select(func.count(CodeChunk.id)).where(CodeChunk.generation_id == gen.id)
        total_chunks_res = await db.execute(total_chunks_stmt)
        if total_chunks_res is not None and hasattr(total_chunks_res, "scalar"):
            tc_val = total_chunks_res.scalar()
            total_chunks = int(tc_val) if tc_val is not None else 0
    except Exception:
        pass

    from app.services.progress_publisher import ProgressStreamPublisher
    publisher = ProgressStreamPublisher()
    await publisher.publish_progress(
        generation_id=gen.id,
        payload={
            "status": "completed",
            "phase": "completed",
            "phase_name": "Indexing complete",
            "files_total": total_files,
            "files_processed": total_files,
            "chunks_total": total_chunks,
            "chunks_processed": total_chunks,
            "progress_percentage": 100.0,
            "estimated_seconds_remaining": 0,
        },
        is_terminal=True,
    )

    from app.services.progress_tracker import IndexingProgressTracker
    tracker = IndexingProgressTracker.get_instance()
    tracker.set_completed(repo.id, files_indexed=total_files, chunks_indexed=total_chunks)

    # Supersede previous active generation if distinct
    if previous_active_id and previous_active_id != gen.id:
        prev_stmt = (
            select(IndexGeneration)
            .where(IndexGeneration.id == previous_active_id)
            .with_for_update()
        )
        prev_res = await db.execute(prev_stmt)
        prev_gen = prev_res.scalar_one_or_none()

        if prev_gen and prev_gen.status == "completed":
            prev_gen.status = "superseded"
            prev_gen.terminal_at = now_utc
            prev_gen.updated_at = now_utc
            await publisher.publish_progress(
                generation_id=prev_gen.id,
                payload={
                    "status": "superseded",
                    "phase": "superseded",
                    "phase_name": "Indexing superseded",
                },
                is_terminal=True,
            )

    return {
        "status": "completed",
        "active_generation_id": str(gen.id),
        "previous_active_id": str(previous_active_id) if previous_active_id else None,
    }
