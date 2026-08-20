"""Parser task and stage lease fencing logic for Subsystem 2.

Parser Task & Stage Lease Fencing
- Atomic stage lease claim (stage_lease_owner, stage_lease_expires_at, stage_attempt)
- Commit SHA freezing (resolve once, reuse on retries)
- Retry cleanup (delete incomplete staged rows on takeover)
- Ephemeral workspace handling
- Fenced DB writes (verify parser fence before every staging transaction)
- Monotonic state transition (preparing -> parsing -> embedding / finalizing)
- Atomic parser checkpoint (create batches, outbox events, update generation state)
"""

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    CodeChunk,
    CodeEmbedding,
    CodeFile,
    DependencyEdge,
    EmbeddingBatch,
    IndexGeneration,
    OutboxEvent,
    Repository,
    Symbol,
)
from app.services.git_service import GitService

logger = logging.getLogger(__name__)


class FenceCheckFailedError(Exception):
    """Raised when parser fence check fails during staging or checkpoint."""
    pass


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def claim_parser_stage_lease(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    lease_duration_minutes: int = 125,
) -> Optional[dict[str, Any]]:
    """Atomically claim parser stage lease for generation_id.
    
    Claim conditions:
    1. Repository.desired_generation_id == generation_id
    2. IndexGeneration.status == 'queued' OR (stage_lease_expires_at expired AND status IN ('preparing', 'parsing'))
    3. IndexGeneration status NOT IN terminal states
    """
    now_utc = get_utc_now()
    lease_expires = now_utc + func.make_interval(0, 0, 0, 0, 0, lease_duration_minutes)  # Or python datetime offset

    # Subquery for desired generation
    desired_subquery = (
        select(Repository.id)
        .where(Repository.desired_generation_id == generation_id)
        .scalar_subquery()
    )

    stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.repository_id == desired_subquery,
            or_(
                IndexGeneration.status == "queued",
                and_(
                    IndexGeneration.stage_lease_expires_at.is_not(None),
                    IndexGeneration.stage_lease_expires_at < now_utc,
                    IndexGeneration.status.in_(["preparing", "parsing"]),
                ),
            ),
            IndexGeneration.status.not_in(["completed", "failed", "cancelled", "superseded"]),
        )
        .values(
            status="preparing",
            stage_lease_owner=task_id,
            stage_lease_expires_at=now_utc + datetime.resolution * 0 + func.cast(
                f"{lease_duration_minutes} minutes", type_=IndexGeneration.stage_lease_expires_at.type
            ) if False else (now_utc.replace(tzinfo=timezone.utc) + func.cast(f"{lease_duration_minutes} minutes", Any) if False else None),
            stage_attempt=IndexGeneration.stage_attempt + 1,
            updated_at=now_utc,
        )
    )

    # Simplified SQLAlchemy update values with Python datetime for cross-DB (Postgres/SQLite) safety in tests:
    from datetime import timedelta
    lease_expires_dt = now_utc + timedelta(minutes=lease_duration_minutes)

    stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.repository_id == desired_subquery,
            or_(
                IndexGeneration.status == "queued",
                and_(
                    IndexGeneration.stage_lease_expires_at.is_not(None),
                    IndexGeneration.stage_lease_expires_at < now_utc,
                    IndexGeneration.status.in_(["preparing", "parsing"]),
                ),
            ),
            IndexGeneration.status.not_in(["completed", "failed", "cancelled", "superseded"]),
        )
        .values(
            status="preparing",
            stage_lease_owner=task_id,
            stage_lease_expires_at=lease_expires_dt,
            stage_attempt=IndexGeneration.stage_attempt + 1,
            updated_at=now_utc,
        )
        .returning(
            IndexGeneration.id,
            IndexGeneration.repository_id,
            IndexGeneration.requested_ref,
            IndexGeneration.commit_sha,
            IndexGeneration.stage_attempt,
            IndexGeneration.pipeline_version,
            IndexGeneration.parser_version,
            IndexGeneration.chunker_version,
            IndexGeneration.embedding_backend,
            IndexGeneration.embedding_model,
            IndexGeneration.embedding_dimension,
            IndexGeneration.embedding_config_hash,
        )
    )

    res = await db.execute(stmt)
    row = res.fetchone()
    if not row:
        return None

    from app.services.progress_publisher import ProgressStreamPublisher
    publisher = ProgressStreamPublisher()
    await publisher.publish_progress(
        generation_id=row.id,
        payload={
            "status": "preparing",
            "phase": "preparing",
            "phase_name": "Preparing repository workspace",
            "stage_attempt": row.stage_attempt,
        },
    )

    return {
        "id": row.id,
        "repository_id": row.repository_id,
        "requested_ref": row.requested_ref,
        "commit_sha": row.commit_sha,
        "stage_attempt": row.stage_attempt,
        "pipeline_version": row.pipeline_version,
        "parser_version": row.parser_version,
        "chunker_version": row.chunker_version,
        "embedding_backend": row.embedding_backend,
        "embedding_model": row.embedding_model,
        "embedding_dimension": row.embedding_dimension,
        "embedding_config_hash": row.embedding_config_hash,
    }


async def verify_parser_fence(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    claimed_attempt: int,
) -> bool:
    """Verify that parser lease fence holds and generation is still desired."""
    now_utc = get_utc_now()
    desired_subquery = (
        select(Repository.id)
        .where(Repository.desired_generation_id == generation_id)
        .scalar_subquery()
    )

    stmt = select(IndexGeneration.id).where(
        IndexGeneration.id == generation_id,
        IndexGeneration.stage_lease_owner == task_id,
        IndexGeneration.stage_attempt == claimed_attempt,
        IndexGeneration.stage_lease_expires_at > now_utc,
        IndexGeneration.status.in_(["preparing", "parsing"]),
        IndexGeneration.repository_id == desired_subquery,
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def resolve_and_freeze_commit_sha(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    claimed_attempt: int,
    git_service: GitService,
    repo_path: Path,
    requested_ref: str,
    current_commit_sha: Optional[str] = None,
) -> str:
    """Resolve requested_ref to commit SHA if NULL, and freeze it under fence."""
    if current_commit_sha:
        return current_commit_sha

    # Resolve symbolic ref to full commit SHA
    try:
        resolved_sha = git_service.resolve_ref_to_sha(repo_path, requested_ref)
    except Exception:
        stmt_repo = (
            select(Repository.local_path)
            .join(IndexGeneration, Repository.id == IndexGeneration.repository_id)
            .where(IndexGeneration.id == generation_id)
        )
        res_repo = await db.execute(stmt_repo)
        local_path = res_repo.scalar_one_or_none()
        if local_path:
            resolved_sha = git_service.resolve_ref_to_sha(local_path, requested_ref)
        else:
            raise

    now_utc = get_utc_now()
    fence_valid = await verify_parser_fence(db, generation_id, task_id, claimed_attempt)
    if not fence_valid:
        raise FenceCheckFailedError("Fence check failed while freezing commit SHA.")

    stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.stage_lease_owner == task_id,
            IndexGeneration.stage_attempt == claimed_attempt,
        )
        .values(commit_sha=resolved_sha, updated_at=now_utc)
    )
    await db.execute(stmt)
    return resolved_sha


async def cleanup_incomplete_staged_rows(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    claimed_attempt: int,
) -> None:
    """Delete incomplete staged rows for generation on lease takeover / retry."""
    fence_valid = await verify_parser_fence(db, generation_id, task_id, claimed_attempt)
    if not fence_valid:
        raise FenceCheckFailedError("Fence check failed before cleanup of incomplete staged rows.")

    # Order of deletion respects foreign keys
    await db.execute(delete(CodeEmbedding).where(CodeEmbedding.generation_id == generation_id))
    await db.execute(delete(CodeChunk).where(CodeChunk.generation_id == generation_id))
    await db.execute(delete(DependencyEdge).where(DependencyEdge.generation_id == generation_id))
    await db.execute(delete(Symbol).where(Symbol.generation_id == generation_id))
    await db.execute(delete(CodeFile).where(CodeFile.generation_id == generation_id))
    await db.execute(delete(EmbeddingBatch).where(EmbeddingBatch.generation_id == generation_id))


async def transition_preparing_to_parsing(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    claimed_attempt: int,
) -> None:
    """Transition IndexGeneration status from preparing -> parsing under fence."""
    now_utc = get_utc_now()
    fence_valid = await verify_parser_fence(db, generation_id, task_id, claimed_attempt)
    if not fence_valid:
        raise FenceCheckFailedError("Fence check failed before status transition to parsing.")

    stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.stage_lease_owner == task_id,
            IndexGeneration.stage_attempt == claimed_attempt,
            IndexGeneration.status == "preparing",
        )
        .values(status="parsing", updated_at=now_utc)
    )
    await db.execute(stmt)

    from app.services.progress_publisher import ProgressStreamPublisher
    publisher = ProgressStreamPublisher()
    await publisher.publish_progress(
        generation_id=generation_id,
        payload={
            "status": "parsing",
            "phase": "parsing",
            "phase_name": "Parsing repository files",
        },
    )


def get_ephemeral_workspace_path(generation_id: UUID, commit_sha: str) -> Path:
    """Return workspace path: /workspaces/{generation_id}/{commit_sha}"""
    base_dir = Path(settings.GITVANE_WORKSPACE)
    return base_dir / "workspaces" / str(generation_id) / commit_sha


async def final_parser_checkpoint(
    db: AsyncSession,
    generation_id: UUID,
    task_id: str,
    claimed_attempt: int,
    chunks: list[CodeChunk],
    embedding_backend: str,
    batch_size: int = settings.EMBEDDING_BATCH_SIZE,
) -> dict[str, Any]:
    """Atomic parser completion checkpoint.
    
    Verifies parser fence and desired generation in one transaction:
    - If N > 0 batches: creates EmbeddingBatch rows, creates embedding_batch_requested outbox events,
      transitions generation to 'embedding', clears stage lease fields.
    - If N == 0: transitions generation to 'finalizing', creates activation_requested outbox event,
      clears stage lease fields.
    """
    now_utc = get_utc_now()
    fence_valid = await verify_parser_fence(db, generation_id, task_id, claimed_attempt)
    if not fence_valid:
        raise FenceCheckFailedError("Fence check failed at final parser checkpoint.")

    total_chunks = len(chunks)
    from app.services.progress_publisher import ProgressStreamPublisher
    publisher = ProgressStreamPublisher()

    if total_chunks > 0:
        num_batches = math.ceil(total_chunks / batch_size)
        batch_rows = []
        outbox_events = []

        for b in range(num_batches):
            start_idx = b * batch_size
            end_idx = min(start_idx + batch_size, total_chunks)
            chunk_start_id = chunks[start_idx].id if hasattr(chunks[start_idx], "id") and chunks[start_idx].id else start_idx + 1
            chunk_end_id = chunks[end_idx - 1].id if hasattr(chunks[end_idx - 1], "id") and chunks[end_idx - 1].id else end_idx

            batch = EmbeddingBatch(
                id=uuid4(),
                generation_id=generation_id,
                batch_index=b,
                status="pending",
                chunk_start_id=chunk_start_id,
                chunk_end_id=chunk_end_id,
                attempt_count=0,
            )
            batch_rows.append(batch)

            event = OutboxEvent(
                id=uuid4(),
                aggregate_id=generation_id,
                event_type="embedding_batch_requested",
                payload={
                    "generation_id": str(generation_id),
                    "batch_index": b,
                    "embedding_backend": embedding_backend,
                },
                status="pending",
                next_attempt_at=now_utc,
            )
            outbox_events.append(event)

        db.add_all(batch_rows)
        db.add_all(outbox_events)

        stmt = (
            update(IndexGeneration)
            .where(
                IndexGeneration.id == generation_id,
                IndexGeneration.stage_lease_owner == task_id,
                IndexGeneration.stage_attempt == claimed_attempt,
                IndexGeneration.status == "parsing",
            )
            .values(
                status="embedding",
                stage_lease_owner=None,
                stage_lease_expires_at=None,
                updated_at=now_utc,
            )
        )
        await db.execute(stmt)

        total_files = 0
        try:
            from app.db.models import CodeFile
            tf_res = await db.execute(select(func.count(CodeFile.id)).where(CodeFile.generation_id == generation_id))
            if tf_res is not None and hasattr(tf_res, "scalar"):
                val = tf_res.scalar()
                if isinstance(val, int):
                    total_files = val
        except Exception:
            total_files = 0

        try:
            import json
            redis_client = publisher.get_async_client()
            meta_payload = {
                "total_batches": num_batches,
                "total_chunks": total_chunks,
                "total_files": total_files,
            }
            await redis_client.set(
                f"gitvane:generation:meta:{generation_id}",
                json.dumps(meta_payload),
                ex=7200,
            )
        except Exception as meta_exc:
            logger.debug("Failed to cache generation metadata in Redis: %s", meta_exc)

        await publisher.publish_progress(
            generation_id=generation_id,
            payload={
                "status": "indexing",
                "phase": "embedding",
                "phase_name": f"Generating embeddings ({num_batches} batches)",
                "files_total": total_files,
                "files_processed": total_files,
                "chunks_total": total_chunks,
                "chunks_processed": 0,
                "batches_total": num_batches,
                "progress_percentage": 50.0,
                "estimated_seconds_remaining": None,
            },
        )
        return {"next_status": "embedding", "num_batches": num_batches}

    else:
        # N == 0: no chunks, go straight to finalizing
        event = OutboxEvent(
            id=uuid4(),
            aggregate_id=generation_id,
            event_type="activation_requested",
            payload={"generation_id": str(generation_id)},
            status="pending",
            next_attempt_at=now_utc,
        )
        db.add(event)

        stmt = (
            update(IndexGeneration)
            .where(
                IndexGeneration.id == generation_id,
                IndexGeneration.stage_lease_owner == task_id,
                IndexGeneration.stage_attempt == claimed_attempt,
                IndexGeneration.status == "parsing",
            )
            .values(
                status="finalizing",
                stage_lease_owner=None,
                stage_lease_expires_at=None,
                updated_at=now_utc,
            )
        )
        await db.execute(stmt)

        await publisher.publish_progress(
            generation_id=generation_id,
            payload={
                "status": "finalizing",
                "phase": "finalizing",
                "phase_name": "Finalizing indexing",
            },
        )
        return {"next_status": "finalizing", "num_batches": 0}
