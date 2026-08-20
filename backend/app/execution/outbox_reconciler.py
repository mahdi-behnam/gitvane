"""Outbox Reconciler Service for GitVane execution engine.

Executes independent short-transaction reconciliation passes for:
1. Expired outbox processing leases (processing -> pending).
2. Expired parser stage leases for desired generations (preparing/parsing -> queued + prepare_requested outbox event).
3. Expired embedding batch leases for desired generations (processing -> pending + embedding_batch_requested outbox event).
4. Stuck finalizing desired generations (inserting safety activation_requested outbox event if none pending/processing).
"""

import asyncio
import logging
import signal
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import EmbeddingBatch, IndexGeneration, OutboxEvent, Repository

logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class OutboxReconciler:
    """Outbox Reconciler service for self-healing expired leases and stuck stages."""

    def __init__(self, reconciler_id: Optional[str] = None):
        self.reconciler_id = reconciler_id or f"reconciler-{uuid4().hex[:6]}"
        self.running = False

    async def recover_expired_outbox_leases(
        self,
        db: AsyncSession,
        lease_timeout_seconds: int = 300,
    ) -> int:
        """Reset outbox events stuck in 'processing' beyond lease timeout back to 'pending'."""
        now_utc = get_utc_now()
        expiry_threshold = now_utc - timedelta(seconds=lease_timeout_seconds)

        stmt = (
            update(OutboxEvent)
            .where(
                OutboxEvent.status == "processing",
                OutboxEvent.locked_at <= expiry_threshold,
            )
            .values(
                status="pending",
                locked_by=None,
                locked_at=None,
            )
        )
        res = await db.execute(stmt)
        await db.commit()

        recovered_count = res.rowcount if hasattr(res, "rowcount") and res.rowcount is not None else 0
        if recovered_count > 0:
            logger.info("Recovered %d expired outbox processing leases", recovered_count)
        return recovered_count

    async def recover_expired_parser_leases(
        self,
        db: AsyncSession,
    ) -> int:
        """Recover generations stuck in preparing/parsing with expired stage lease.
        
        Only recovers if the generation is still Repository.desired_generation_id and non-terminal.
        In 1 transaction per generation: clear lease fields, set status='queued', insert prepare_requested event.
        """
        now_utc = get_utc_now()

        # Find desired generations in preparing/parsing with expired lease
        stmt = (
            select(IndexGeneration)
            .join(Repository, Repository.desired_generation_id == IndexGeneration.id)
            .where(
                IndexGeneration.status.in_(["preparing", "parsing"]),
                IndexGeneration.stage_lease_expires_at.is_not(None),
                IndexGeneration.stage_lease_expires_at <= now_utc,
            )
        )
        res = await db.execute(stmt)
        expired_gens = list(res.scalars().all())

        if not expired_gens:
            return 0

        recovered_count = 0
        for gen in expired_gens:
            # Re-verify inside a lock to prevent race conditions
            lock_stmt = (
                select(IndexGeneration)
                .join(Repository, Repository.desired_generation_id == IndexGeneration.id)
                .where(
                    IndexGeneration.id == gen.id,
                    IndexGeneration.status.in_(["preparing", "parsing"]),
                    IndexGeneration.stage_lease_expires_at <= now_utc,
                )
                .with_for_update()
            )
            lock_res = await db.execute(lock_stmt)
            target_gen = lock_res.scalar_one_or_none()

            if not target_gen:
                continue

            target_gen.stage_lease_owner = None
            target_gen.stage_lease_expires_at = None
            target_gen.status = "queued"
            target_gen.updated_at = now_utc

            outbox_event = OutboxEvent(
                id=uuid4(),
                aggregate_id=target_gen.id,
                event_type="prepare_requested",
                payload={"generation_id": str(target_gen.id)},
                status="pending",
                next_attempt_at=now_utc,
            )
            db.add(outbox_event)
            await db.commit()
            recovered_count += 1
            logger.info("Recovered expired parser lease for desired generation %s", target_gen.id)

        return recovered_count

    async def recover_expired_embedding_batch_leases(
        self,
        db: AsyncSession,
    ) -> int:
        """Recover embedding batches stuck in 'processing' with expired lease.
        
        Only recovers if batch is processing, lease expired, and generation is 'embedding' and desired.
        In 1 transaction per batch: set batch status='pending', clear lease fields, insert embedding_batch_requested event.
        """
        now_utc = get_utc_now()

        stmt = (
            select(EmbeddingBatch, IndexGeneration.embedding_backend)
            .join(IndexGeneration, EmbeddingBatch.generation_id == IndexGeneration.id)
            .join(Repository, Repository.desired_generation_id == IndexGeneration.id)
            .where(
                EmbeddingBatch.status == "processing",
                EmbeddingBatch.lease_expires_at.is_not(None),
                EmbeddingBatch.lease_expires_at <= now_utc,
                IndexGeneration.status == "embedding",
            )
        )
        res = await db.execute(stmt)
        rows = list(res.all())

        if not rows:
            return 0

        recovered_count = 0
        for batch, embedding_backend in rows:
            # Re-verify and lock batch
            lock_stmt = (
                select(EmbeddingBatch)
                .join(IndexGeneration, EmbeddingBatch.generation_id == IndexGeneration.id)
                .join(Repository, Repository.desired_generation_id == IndexGeneration.id)
                .where(
                    EmbeddingBatch.id == batch.id,
                    EmbeddingBatch.status == "processing",
                    EmbeddingBatch.lease_expires_at <= now_utc,
                    IndexGeneration.status == "embedding",
                )
                .with_for_update()
            )
            lock_res = await db.execute(lock_stmt)
            target_batch = lock_res.scalar_one_or_none()

            if not target_batch:
                continue

            target_batch.status = "pending"
            target_batch.lease_owner = None
            target_batch.lease_expires_at = None

            outbox_event = OutboxEvent(
                id=uuid4(),
                aggregate_id=target_batch.generation_id,
                event_type="embedding_batch_requested",
                payload={
                    "generation_id": str(target_batch.generation_id),
                    "batch_index": target_batch.batch_index,
                    "embedding_backend": embedding_backend,
                },
                status="pending",
                next_attempt_at=now_utc,
            )
            db.add(outbox_event)
            await db.commit()
            recovered_count += 1
            logger.info(
                "Recovered expired embedding batch lease for generation %s batch %d",
                target_batch.generation_id,
                target_batch.batch_index,
            )

        return recovered_count

    async def recover_stuck_finalizing_generations(
        self,
        db: AsyncSession,
        threshold_seconds: int = 120,
    ) -> int:
        """Periodically detect desired generations stuck in 'finalizing' beyond operational threshold.
        
        If no pending or processing activation event exists for the generation, insert a new activation_requested OutboxEvent.
        """
        now_utc = get_utc_now()
        stuck_threshold = now_utc - timedelta(seconds=threshold_seconds)

        stmt = (
            select(IndexGeneration)
            .join(Repository, Repository.desired_generation_id == IndexGeneration.id)
            .where(
                IndexGeneration.status == "finalizing",
                IndexGeneration.updated_at <= stuck_threshold,
            )
        )
        res = await db.execute(stmt)
        stuck_gens = list(res.scalars().all())

        if not stuck_gens:
            return 0

        recovered_count = 0
        for gen in stuck_gens:
            # Check if an active activation_requested event already exists
            active_event_stmt = select(OutboxEvent.id).where(
                OutboxEvent.aggregate_id == gen.id,
                OutboxEvent.event_type == "activation_requested",
                OutboxEvent.status.in_(["pending", "processing"]),
            )
            active_event_res = await db.execute(active_event_stmt)
            existing_event = active_event_res.scalar_one_or_none()

            if existing_event:
                continue

            outbox_event = OutboxEvent(
                id=uuid4(),
                aggregate_id=gen.id,
                event_type="activation_requested",
                payload={"generation_id": str(gen.id)},
                status="pending",
                next_attempt_at=now_utc,
            )
            db.add(outbox_event)
            await db.commit()
            recovered_count += 1
            logger.info("Inserted safety activation_requested event for stuck finalizing generation %s", gen.id)

        return recovered_count

    async def run_reconciliation_pass(
        self,
        db_factory: async_sessionmaker[AsyncSession],
        outbox_lease_seconds: int = 300,
        finalizing_threshold_seconds: int = 120,
    ) -> dict[str, int]:
        """Execute all reconciliation recovery checks in independent short transactions."""
        summary = {}

        async with db_factory() as db:
            summary["outbox_leases_reset"] = await self.recover_expired_outbox_leases(
                db, lease_timeout_seconds=outbox_lease_seconds
            )

        async with db_factory() as db:
            summary["parser_leases_recovered"] = await self.recover_expired_parser_leases(db)

        async with db_factory() as db:
            summary["embedding_batch_leases_recovered"] = await self.recover_expired_embedding_batch_leases(db)

        async with db_factory() as db:
            summary["finalizing_safety_events_created"] = await self.recover_stuck_finalizing_generations(
                db, threshold_seconds=finalizing_threshold_seconds
            )

        return summary

    async def run_forever(
        self,
        db_factory: async_sessionmaker[AsyncSession],
        poll_interval: float = 10.0,
        outbox_lease_seconds: int = 300,
        finalizing_threshold_seconds: int = 120,
    ) -> None:
        """Run reconciler daemon loop with graceful shutdown signal handling."""
        self.running = True
        logger.info(
            "GitVane OutboxReconciler is ready and monitoring leases [reconciler_id=%s, poll_interval=%.1fs, outbox_lease_timeout=%ds, finalizing_threshold=%ds]",
            self.reconciler_id,
            poll_interval,
            outbox_lease_seconds,
            finalizing_threshold_seconds,
        )

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown, sig)
            except (NotImplementedError, RuntimeError):
                pass

        while self.running:
            try:
                summary = await self.run_reconciliation_pass(
                    db_factory=db_factory,
                    outbox_lease_seconds=outbox_lease_seconds,
                    finalizing_threshold_seconds=finalizing_threshold_seconds,
                )
                total_recovered = sum(summary.values())
                if total_recovered > 0:
                    logger.info("Reconciliation pass complete: %s", summary)

                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info("OutboxReconciler loop cancelled.")
                break
            except Exception as exc:
                logger.exception("Unexpected error in OutboxReconciler loop: %s", exc)
                await asyncio.sleep(poll_interval)

        logger.info("OutboxReconciler loop stopped gracefully.")

    def _handle_shutdown(self, sig: int) -> None:
        logger.info("Received shutdown signal %s. Stopping OutboxReconciler...", sig)
        self.running = False
