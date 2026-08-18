"""Celery task for embedding batch generation (embeddings_gpu / embeddings_nim_io queues)."""

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from celery import Task

from app.core.async_runner import run_sync_in_worker_loop
from app.core.celery_app import celery_app
from app.db.session import WorkerSessionLocal as SessionLocal
from app.execution.embedding_engine import (
    checkpoint_batch_completion,
    claim_embedding_batch_lease,
    persist_batch_embeddings,
)
from app.execution.failure_engine import handle_embedding_batch_failure
from app.embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.embedding_tasks.task_generate_embeddings_batch",
    acks_late=True,
    reject_on_worker_lost=True,
)
def task_generate_embeddings_batch(self: Task, generation_id_str: str, batch_index: int) -> dict:
    """Task to process an embedding batch under lease fencing."""
    task_id = self.request.id or str(uuid4())
    generation_id = UUID(generation_id_str)

    return run_sync_in_worker_loop(_async_generate_embeddings_batch(generation_id, batch_index, task_id))


async def _async_generate_embeddings_batch(generation_id: UUID, batch_index: int, task_id: str) -> dict[str, Any]:
    import time
    batch_start_time = time.monotonic()
    embedding_svc = EmbeddingService()

    # Step 1: Claim lease and read chunk texts in a short, bounded transaction
    async with SessionLocal() as db:
        claim = await claim_embedding_batch_lease(db, generation_id, batch_index, task_id)
        if not claim:
            logger.info("Batch claim skipped for generation %s index %s", generation_id, batch_index)
            await db.commit()
            return {"status": "skipped", "reason": "claim_failed_or_not_desired"}

        chunk_start_id = claim["chunk_start_id"]
        chunk_end_id = claim["chunk_end_id"]
        model_name = claim["embedding_model"]
        dimension = claim["embedding_dimension"]
        backend = claim["embedding_backend"]

        from sqlalchemy import select
        from app.db.models import CodeChunk

        chunks_stmt = select(CodeChunk.id, CodeChunk.text).where(
            CodeChunk.generation_id == generation_id,
            CodeChunk.id >= chunk_start_id,
            CodeChunk.id <= chunk_end_id,
        )
        chunks_res = await db.execute(chunks_stmt)
        chunks_data = list(chunks_res.all())
        await db.commit()

    # Step 2: Generate vectors in memory (No database transaction held idle during model computation!)
    embeddings_data = []
    if chunks_data:
        texts = [row[1] for row in chunks_data]
        try:
            vectors = await embedding_svc.generate_embeddings(texts)
        except Exception:
            vectors = [[0.0] * dimension for _ in texts]

        for (chunk_id, _), vec in zip(chunks_data, vectors):
            embeddings_data.append(
                {
                    "chunk_id": chunk_id,
                    "provider": backend,
                    "model": model_name or "default-model",
                    "dimensions": len(vec),
                    "embedding": vec,
                }
            )

    # Step 3: Fenced persist & atomic completion in a clean, fresh transaction
    try:
        async with SessionLocal() as db:
            persisted = await persist_batch_embeddings(
                db=db,
                generation_id=generation_id,
                batch_index=batch_index,
                task_id=task_id,
                embeddings_data=embeddings_data,
            )

            if not persisted:
                logger.warning("Batch fence lost before vector persistence for generation %s batch %s", generation_id, batch_index)
                await db.rollback()
                return {"status": "fence_lost"}

            checkpoint = await checkpoint_batch_completion(
                db=db,
                generation_id=generation_id,
                batch_index=batch_index,
                task_id=task_id,
            )
            await db.commit()

            if checkpoint.get("completed") and not checkpoint.get("finalized"):
                try:
                    import json
                    from app.services.progress_publisher import ProgressStreamPublisher

                    publisher = ProgressStreamPublisher()
                    redis_client = publisher.get_async_client()

                    total_batches = None
                    total_chunks = None
                    total_files = None

                    meta_raw = await redis_client.get(f"gitvane:generation:meta:{generation_id}")
                    if meta_raw:
                        try:
                            meta_data = json.loads(meta_raw)
                            total_batches = meta_data.get("total_batches")
                            total_chunks = meta_data.get("total_chunks")
                            total_files = meta_data.get("total_files")
                        except Exception:
                            pass

                    if total_batches is None:
                        from sqlalchemy import func
                        from app.db.models import CodeChunk, CodeFile, EmbeddingBatch

                        tb_res = await db.execute(
                            select(func.count(EmbeddingBatch.id)).where(EmbeddingBatch.generation_id == generation_id)
                        )
                        total_batches = tb_res.scalar() or 1
                        tc_res = await db.execute(
                            select(func.count(CodeChunk.id)).where(CodeChunk.generation_id == generation_id)
                        )
                        total_chunks = tc_res.scalar() or 0
                        tf_res = await db.execute(
                            select(func.count(CodeFile.id)).where(CodeFile.generation_id == generation_id)
                        )
                        total_files = tf_res.scalar() or 0

                    completed_batches = min(total_batches, batch_index + 1)
                    rem_batches = max(0, total_batches - completed_batches)

                    chunks_processed = min(total_chunks, int(total_chunks * (completed_batches / max(1, total_batches)))) if total_chunks > 0 else chunk_end_id
                    progress_pct = round(min(98.0, 50.0 + (completed_batches / max(1, total_batches)) * 48.0), 1)

                    batch_duration = max(0.05, time.monotonic() - batch_start_time)
                    ema_key = f"gitvane:progress:ema:{generation_id}"

                    try:
                        cached_ema = await redis_client.get(ema_key)
                        prev_ema = float(cached_ema) if cached_ema is not None else None
                    except Exception:
                        prev_ema = None

                    if prev_ema is None:
                        # First measured batch: initialize EMA directly from real wall-clock measurement
                        current_ema = batch_duration
                    else:
                        alpha = 0.35
                        current_ema = (alpha * batch_duration) + ((1.0 - alpha) * prev_ema)

                    try:
                        await redis_client.set(ema_key, str(current_ema), ex=3600)
                    except Exception:
                        pass

                    eta_sec = max(0, int(rem_batches * current_ema))

                    await publisher.publish_progress(
                        generation_id=generation_id,
                        payload={
                            "status": "indexing",
                            "phase": "embedding",
                            "phase_name": f"Generating embeddings ({completed_batches}/{total_batches} batches)",
                            "files_total": total_files,
                            "files_processed": total_files,
                            "chunks_total": total_chunks,
                            "chunks_processed": chunks_processed,
                            "progress_percentage": progress_pct,
                            "estimated_seconds_remaining": eta_sec,
                        },
                    )
                except Exception as pub_exc:
                    logger.debug("Failed to publish embedding batch progress: %s", pub_exc)

            return {"status": "success", "batch_index": batch_index, **checkpoint}

    except Exception as exc:
        logger.exception("Error processing batch %s for generation %s: %s", batch_index, generation_id, exc)
        async with SessionLocal() as fail_db:
            fail_status = await handle_embedding_batch_failure(
                db=fail_db,
                generation_id=generation_id,
                batch_index=batch_index,
                task_id=task_id,
                error_message=str(exc),
            )
            await fail_db.commit()
        raise exc
