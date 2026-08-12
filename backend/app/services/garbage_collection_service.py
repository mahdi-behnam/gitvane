"""Garbage Collection Service for GitVane Index Generations.

Section 17: Garbage Collection
- Identifies eligible generations: status IN ('superseded', 'failed', 'cancelled')
  AND terminal_at < now() - interval '24 hours'.
- Defense-in-depth safety checks strictly protect any active_generation_id or desired_generation_id.
- Batch deletion per transaction (LIMIT 100 / LIMIT 1000) prevents table locks and WAL spikes.
- Strictly deletes in FK dependency order:
  CodeEmbedding -> CodeChunk -> DependencyEdge -> Symbol -> CodeFile -> EmbeddingBatch.
- Retains IndexGeneration metadata record for audit/diagnostics by updating cleaned_at = now().
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Set
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CodeChunk,
    CodeEmbedding,
    CodeFile,
    DependencyEdge,
    EmbeddingBatch,
    IndexGeneration,
    Repository,
    Symbol,
)

logger = logging.getLogger(__name__)

ELIGIBLE_GC_STATUSES = {"superseded", "failed", "cancelled"}
DEFAULT_RETENTION_HOURS = 24
DEFAULT_BATCH_SIZE = 1000


class GarbageCollectionService:
    """Service to handle periodic cleanup of stale index generation data."""

    async def get_protected_generation_ids(self, db: AsyncSession) -> Set[UUID]:
        """Returns the set of generation IDs that are currently active or desired across all repositories."""
        protected: Set[UUID] = set()

        # Query active_generation_id
        active_stmt = select(Repository.active_generation_id).where(
            Repository.active_generation_id.is_not(None)
        )
        active_res = await db.execute(active_stmt)
        for gen_id in active_res.scalars().all():
            if gen_id:
                protected.add(gen_id)

        # Query desired_generation_id
        desired_stmt = select(Repository.desired_generation_id).where(
            Repository.desired_generation_id.is_not(None)
        )
        desired_res = await db.execute(desired_stmt)
        for gen_id in desired_res.scalars().all():
            if gen_id:
                protected.add(gen_id)

        return protected

    async def find_eligible_generations(
        self,
        db: AsyncSession,
        retention_hours: int = DEFAULT_RETENTION_HOURS,
        limit: int = 100,
    ) -> List[IndexGeneration]:
        """Finds generations eligible for garbage collection.

        Criteria:
        - status IN ('superseded', 'failed', 'cancelled')
        - terminal_at < now() - interval '24 hours'
        - cleaned_at IS NULL (not yet cleaned)
        - NOT referenced by active_generation_id or desired_generation_id
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        protected_ids = await self.get_protected_generation_ids(db)

        stmt = select(IndexGeneration).where(
            IndexGeneration.status.in_(ELIGIBLE_GC_STATUSES),
            IndexGeneration.terminal_at.is_not(None),
            IndexGeneration.terminal_at < cutoff,
            IndexGeneration.cleaned_at.is_(None),
        )

        if protected_ids:
            stmt = stmt.where(IndexGeneration.id.not_in(protected_ids))

        stmt = stmt.limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def cleanup_generation(
        self,
        db: AsyncSession,
        generation_id: UUID,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Dict[str, int]:
        """Deletes all graph, chunk, and embedding rows for a generation in strict FK dependency order with bounded transaction batches.

        FK Order:
        1. CodeEmbedding
        2. CodeChunk
        3. DependencyEdge
        4. Symbol
        5. CodeFile
        6. EmbeddingBatch
        """
        deleted_counts: Dict[str, int] = {
            "code_embeddings": 0,
            "code_chunks": 0,
            "dependency_edges": 0,
            "symbols": 0,
            "code_files": 0,
            "embedding_batches": 0,
        }

        # Double check protection fence
        protected_ids = await self.get_protected_generation_ids(db)
        if generation_id in protected_ids:
            logger.warning(
                "Aborting GC for generation %s: generation is protected as active/desired.",
                generation_id,
            )
            return deleted_counts

        # Helper function for bounded batch deletion per table
        async def _batch_delete_model(model: Any, model_key: str) -> None:
            while True:
                subq = (
                    select(model.id)
                    .where(model.generation_id == generation_id)
                    .limit(batch_size)
                    .scalar_subquery()
                )
                del_stmt = delete(model).where(model.id.in_(subq))
                res = await db.execute(del_stmt)
                count = res.rowcount or 0
                deleted_counts[model_key] += count
                await db.commit()
                if count < batch_size:
                    break

        # 1. CodeEmbedding
        await _batch_delete_model(CodeEmbedding, "code_embeddings")

        # 2. CodeChunk
        await _batch_delete_model(CodeChunk, "code_chunks")

        # 3. DependencyEdge
        await _batch_delete_model(DependencyEdge, "dependency_edges")

        # 4. Symbol
        await _batch_delete_model(Symbol, "symbols")

        # 5. CodeFile
        await _batch_delete_model(CodeFile, "code_files")

        # 6. EmbeddingBatch
        await _batch_delete_model(EmbeddingBatch, "embedding_batches")

        # 7. Update IndexGeneration record with cleaned_at timestamp
        update_stmt = (
            update(IndexGeneration)
            .where(IndexGeneration.id == generation_id)
            .values(cleaned_at=func.now())
        )
        await db.execute(update_stmt)
        await db.commit()

        logger.info(
            "Garbage collection completed for generation %s: %s",
            generation_id,
            deleted_counts,
        )
        return deleted_counts

    async def run_garbage_collection(
        self,
        db: AsyncSession,
        retention_hours: int = DEFAULT_RETENTION_HOURS,
        generation_limit: int = 100,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Dict[str, Any]:
        """Runs periodic garbage collection over eligible stale generations."""
        eligible = await self.find_eligible_generations(
            db, retention_hours=retention_hours, limit=generation_limit
        )

        results: Dict[str, Any] = {
            "eligible_count": len(eligible),
            "cleaned_count": 0,
            "skipped_count": 0,
            "generations_cleaned": [],
            "total_rows_deleted": {
                "code_embeddings": 0,
                "code_chunks": 0,
                "dependency_edges": 0,
                "symbols": 0,
                "code_files": 0,
                "embedding_batches": 0,
            },
        }

        for gen in eligible:
            # Refresh protected set to ensure strict defense-in-depth safety
            protected_ids = await self.get_protected_generation_ids(db)
            if gen.id in protected_ids:
                logger.info(
                    "Skipping generation %s during GC run: referenced as active or desired.",
                    gen.id,
                )
                results["skipped_count"] += 1
                continue

            try:
                counts = await self.cleanup_generation(db, gen.id, batch_size=batch_size)
                results["cleaned_count"] += 1
                results["generations_cleaned"].append(str(gen.id))
                for key, val in counts.items():
                    results["total_rows_deleted"][key] += val
            except Exception as e:
                logger.exception("Failed to garbage collect generation %s: %s", gen.id, e)
                try:
                    res = db.rollback()
                    if hasattr(res, "__await__"):
                        await res
                except Exception:
                    pass

        return results
