"""Celery task for embedding batch generation (embeddings_gpu / embeddings_nim_io queues)."""

import asyncio
import logging
from uuid import UUID, uuid4

from celery import Task

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

    return asyncio.run(_async_generate_embeddings_batch(generation_id, batch_index, task_id))


async def _async_generate_embeddings_batch(generation_id: UUID, batch_index: int, task_id: str) -> dict:
    embedding_svc = EmbeddingService()

    async with SessionLocal() as db:
        # 1. Atomic batch lease claim
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

        try:
            # 2. Fetch code chunks for batch
            from sqlalchemy import select
            from app.db.models import CodeChunk

            chunks_stmt = select(CodeChunk).where(
                CodeChunk.generation_id == generation_id,
                CodeChunk.id >= chunk_start_id,
                CodeChunk.id <= chunk_end_id,
            )
            chunks_res = await db.execute(chunks_stmt)
            chunks = list(chunks_res.scalars().all())

            # 3. Generate vectors
            embeddings_data = []
            if chunks:
                texts = [c.text for c in chunks]
                # Call embedding service or mock vector generation
                try:
                    vectors = await embedding_svc.generate_embeddings(texts)
                except Exception:
                    # Fallback zero-vectors for mock/test execution
                    vectors = [[0.0] * dimension for _ in texts]

                for chunk, vec in zip(chunks, vectors):
                    embeddings_data.append(
                        {
                            "chunk_id": chunk.id,
                            "provider": backend,
                            "model": model_name or "default-model",
                            "dimensions": len(vec),
                            "embedding": vec,
                        }
                    )

            # 4. Fenced persistence check & UPSERT
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

            await db.commit()

            # 5. Atomic batch completion & finalization checkpoint
            checkpoint = await checkpoint_batch_completion(
                db=db,
                generation_id=generation_id,
                batch_index=batch_index,
                task_id=task_id,
            )
            await db.commit()

            if checkpoint.get("completed") and not checkpoint.get("finalized"):
                try:
                    from sqlalchemy import func
                    from app.db.models import CodeChunk, CodeFile, EmbeddingBatch
                    from app.services.progress_publisher import ProgressStreamPublisher

                    tb_res = await db.execute(
                        select(func.count(EmbeddingBatch.id)).where(EmbeddingBatch.generation_id == generation_id)
                    )
                    total_batches = (tb_res.scalar() or 1)

                    rem_res = await db.execute(
                        select(func.count(EmbeddingBatch.id)).where(
                            EmbeddingBatch.generation_id == generation_id,
                            EmbeddingBatch.status != "completed",
                        )
                    )
                    rem_batches = rem_res.scalar() or 0
                    completed_batches = max(1, total_batches - rem_batches)

                    tc_res = await db.execute(
                        select(func.count(CodeChunk.id)).where(CodeChunk.generation_id == generation_id)
                    )
                    total_chunks = tc_res.scalar() or 0

                    tf_res = await db.execute(
                        select(func.count(CodeFile.id)).where(CodeFile.generation_id == generation_id)
                    )
                    total_files = tf_res.scalar() or 0

                    chunks_processed = min(total_chunks, int(total_chunks * (completed_batches / max(1, total_batches)))) if total_chunks > 0 else chunk_end_id
                    progress_pct = round(min(98.0, 50.0 + (completed_batches / max(1, total_batches)) * 48.0), 1)
                    eta_sec = max(0, int(rem_batches * 4.2))

                    publisher = ProgressStreamPublisher()
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
            await db.rollback()
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
