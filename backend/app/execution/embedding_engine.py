"""Embedding batch task and batch lease fencing logic for Subsystem 2.

Embedding Batch Task & Batch Lease Fencing
- Atomic batch claim with lease (27m local GPU / 8m NIM)
- Vector generation using frozen generation settings
- Fenced persistence check & PostgreSQL UPSERT (ON CONFLICT (generation_id, chunk_id, model))
- Atomic batch completion and finalization checkpoint
  (transitions generation from embedding -> finalizing and inserts activation_requested outbox event)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CodeChunk,
    CodeEmbedding,
    EmbeddingBatch,
    IndexGeneration,
    OutboxEvent,
    Repository,
)


class EmbeddingFenceCheckFailedError(Exception):
    """Raised when embedding batch fence check fails."""
    pass


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def claim_embedding_batch_lease(
    db: AsyncSession,
    generation_id: UUID,
    batch_index: int,
    task_id: str,
) -> Optional[dict[str, Any]]:
    """Atomically claim embedding batch lease.
    
    Claim conditions:
    1. IndexGeneration.id == generation_id AND IndexGeneration.status == 'embedding'
    2. Repository.desired_generation_id == generation_id
    3. EmbeddingBatch status == 'pending' OR (lease_expires_at expired AND status == 'processing')
    """
    now_utc = get_utc_now()

    # Determine backend lease duration: local GPU = 27m, NIM = 8m
    gen_stmt = (
        select(IndexGeneration.embedding_backend)
        .where(IndexGeneration.id == generation_id)
    )
    gen_res = await db.execute(gen_stmt)
    backend_val = gen_res.scalar_one_or_none()
    lease_minutes = 8 if backend_val == "nim" else 27

    lease_expires_dt = now_utc + timedelta(minutes=lease_minutes)

    desired_subquery = (
        select(Repository.id)
        .where(Repository.desired_generation_id == generation_id)
        .scalar_subquery()
    )

    gen_valid_subquery = (
        select(IndexGeneration.id)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.status == "embedding",
            IndexGeneration.repository_id == desired_subquery,
        )
        .scalar_subquery()
    )

    stmt = (
        update(EmbeddingBatch)
        .where(
            EmbeddingBatch.generation_id == gen_valid_subquery,
            EmbeddingBatch.batch_index == batch_index,
            and_(
                EmbeddingBatch.status != "completed",
                or_(
                    EmbeddingBatch.status == "pending",
                    and_(
                        EmbeddingBatch.lease_expires_at.is_not(None),
                        EmbeddingBatch.lease_expires_at < now_utc,
                        EmbeddingBatch.status == "processing",
                    ),
                ),
            ),
        )
        .values(
            status="processing",
            lease_owner=task_id,
            lease_expires_at=lease_expires_dt,
            attempt_count=EmbeddingBatch.attempt_count + 1,
            started_at=now_utc,
        )
        .returning(
            EmbeddingBatch.id,
            EmbeddingBatch.generation_id,
            EmbeddingBatch.batch_index,
            EmbeddingBatch.chunk_start_id,
            EmbeddingBatch.chunk_end_id,
            EmbeddingBatch.attempt_count,
        )
    )

    res = await db.execute(stmt)
    row = res.fetchone()
    if not row:
        return None

    # Fetch generation model details
    gen_details_stmt = select(
        IndexGeneration.embedding_backend,
        IndexGeneration.embedding_model,
        IndexGeneration.embedding_dimension,
        IndexGeneration.embedding_config_hash,
    ).where(IndexGeneration.id == generation_id)
    gen_details_res = await db.execute(gen_details_stmt)
    gen_row = gen_details_res.fetchone()

    return {
        "batch_id": row.id,
        "generation_id": row.generation_id,
        "batch_index": row.batch_index,
        "chunk_start_id": row.chunk_start_id,
        "chunk_end_id": row.chunk_end_id,
        "attempt_count": row.attempt_count,
        "embedding_backend": gen_row.embedding_backend if gen_row else "local",
        "embedding_model": gen_row.embedding_model if gen_row else "",
        "embedding_dimension": gen_row.embedding_dimension if gen_row else 768,
        "embedding_config_hash": gen_row.embedding_config_hash if gen_row else "",
    }


async def verify_embedding_batch_fence(
    db: AsyncSession,
    generation_id: UUID,
    batch_index: int,
    task_id: str,
) -> bool:
    """Verify batch lease fence holds and generation is still desired."""
    now_utc = get_utc_now()
    desired_subquery = (
        select(Repository.id)
        .where(Repository.desired_generation_id == generation_id)
        .scalar_subquery()
    )

    stmt = (
        select(EmbeddingBatch.id)
        .join(IndexGeneration, IndexGeneration.id == EmbeddingBatch.generation_id)
        .where(
            EmbeddingBatch.generation_id == generation_id,
            EmbeddingBatch.batch_index == batch_index,
            EmbeddingBatch.status == "processing",
            EmbeddingBatch.lease_owner == task_id,
            EmbeddingBatch.lease_expires_at > now_utc,
            IndexGeneration.status == "embedding",
            IndexGeneration.repository_id == desired_subquery,
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def persist_batch_embeddings(
    db: AsyncSession,
    generation_id: UUID,
    batch_index: int,
    task_id: str,
    embeddings_data: list[dict[str, Any]],
) -> bool:
    """Fenced vector persistence check & PostgreSQL UPSERT.
    
    ON CONFLICT (generation_id, chunk_id, model) DO UPDATE ...
    """
    fence_valid = await verify_embedding_batch_fence(db, generation_id, batch_index, task_id)
    if not fence_valid:
        return False

    if not embeddings_data:
        return True

    now_utc = get_utc_now()

    # Format records for insert/upsert (deduplicating by conflict target)
    import math

    seen_keys = set()
    insert_values = []
    for item in embeddings_data:
        key = (generation_id, item["chunk_id"], item["model"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        raw_vec = item["embedding"]
        clean_vec = [
            0.0 if (v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))) else float(v)
            for v in raw_vec
        ]
        insert_values.append(
            {
                "generation_id": generation_id,
                "chunk_id": item["chunk_id"],
                "provider": item["provider"],
                "model": item["model"],
                "dimensions": item["dimensions"],
                "embedding": clean_vec,
                "created_at": now_utc,
            }
        )

    dialect_name = db.bind.dialect.name if db.bind is not None else "postgresql"
    if dialect_name == "postgresql":
        stmt = pg_insert(CodeEmbedding).values(insert_values)
        upsert_stmt = stmt.on_conflict_do_update(
            constraint="uq_code_embeddings_gen_chunk_model",
            set_={
                "embedding": stmt.excluded.embedding,
                "provider": stmt.excluded.provider,
                "dimensions": stmt.excluded.dimensions,
                "created_at": stmt.excluded.created_at,
            },
        )
        await db.execute(upsert_stmt)
    else:
        # Fallback for SQLite in unit test environment where pg_insert isn't supported
        for item in insert_values:
            existing_stmt = select(CodeEmbedding).where(
                CodeEmbedding.generation_id == generation_id,
                CodeEmbedding.chunk_id == item["chunk_id"],
                CodeEmbedding.model == item["model"],
            )
            existing_res = await db.execute(existing_stmt)
            existing = existing_res.scalar_one_or_none()
            if existing:
                existing.embedding = item["embedding"]
                existing.provider = item["provider"]
                existing.dimensions = item["dimensions"]
                existing.created_at = item["created_at"]
            else:
                db.add(CodeEmbedding(**item))

    return True


async def checkpoint_batch_completion(
    db: AsyncSession,
    generation_id: UUID,
    batch_index: int,
    task_id: str,
) -> dict[str, bool]:
    """Atomic batch completion & finalization check.
    
    1. Fenced batch update: processing -> completed.
    2. If 1 row updated, check if any non-completed batch remains for generation.
    3. If no non-completed batch remains, transition generation embedding -> finalizing
       and insert OutboxEvent(event_type='activation_requested').
    """
    now_utc = get_utc_now()

    # 1. Fenced batch completion
    stmt = (
        update(EmbeddingBatch)
        .where(
            EmbeddingBatch.generation_id == generation_id,
            EmbeddingBatch.batch_index == batch_index,
            EmbeddingBatch.status == "processing",
            EmbeddingBatch.lease_owner == task_id,
            EmbeddingBatch.lease_expires_at > now_utc,
        )
        .values(
            status="completed",
            completed_at=now_utc,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    res = await db.execute(stmt)
    if res.rowcount == 0:
        return {"completed": False, "finalized": False}

    # 2. Check remaining non-completed batches
    rem_stmt = select(func.count(EmbeddingBatch.id)).where(
        EmbeddingBatch.generation_id == generation_id,
        EmbeddingBatch.status != "completed",
    )
    rem_res = await db.execute(rem_stmt)
    rem_val = rem_res.scalar() if hasattr(rem_res, "scalar") else None
    try:
        remaining_count = int(rem_val) if rem_val is not None else 0
    except (TypeError, ValueError):
        remaining_count = 0

    from app.services.progress_publisher import ProgressStreamPublisher
    publisher = ProgressStreamPublisher()

    if remaining_count > 0:
        return {"completed": True, "finalized": False}

    # 3. All batches completed: transition generation embedding -> finalizing
    desired_subquery = (
        select(Repository.id)
        .where(Repository.desired_generation_id == generation_id)
        .scalar_subquery()
    )

    gen_stmt = (
        update(IndexGeneration)
        .where(
            IndexGeneration.id == generation_id,
            IndexGeneration.status == "embedding",
            IndexGeneration.repository_id == desired_subquery,
        )
        .values(
            status="finalizing",
            updated_at=now_utc,
        )
    )
    gen_res = await db.execute(gen_stmt)
    if gen_res.rowcount > 0:
        # Insert activation_requested OutboxEvent
        event = OutboxEvent(
            id=uuid4(),
            aggregate_id=generation_id,
            event_type="activation_requested",
            payload={"generation_id": str(generation_id)},
            status="pending",
            next_attempt_at=now_utc,
        )
        db.add(event)

        total_chunks = 0
        total_files = 0
        try:
            from app.db.models import CodeFile
            tc_res = await db.execute(select(func.count(CodeChunk.id)).where(CodeChunk.generation_id == generation_id))
            if tc_res is not None and hasattr(tc_res, "scalar"):
                total_chunks = tc_res.scalar() or 0
            tf_res = await db.execute(select(func.count(CodeFile.id)).where(CodeFile.generation_id == generation_id))
            if tf_res is not None and hasattr(tf_res, "scalar"):
                total_files = tf_res.scalar() or 0
        except Exception:
            pass

        await publisher.publish_progress(
            generation_id=generation_id,
            payload={
                "status": "finalizing",
                "phase": "finalizing",
                "phase_name": "Finalizing indexing",
                "files_total": total_files,
                "files_processed": total_files,
                "chunks_total": total_chunks,
                "chunks_processed": total_chunks,
                "progress_percentage": 99.0,
                "estimated_seconds_remaining": 0,
            },
        )
        return {"completed": True, "finalized": True}

    return {"completed": True, "finalized": False}
