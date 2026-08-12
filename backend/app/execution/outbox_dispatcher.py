"""Outbox Dispatcher Service for GitVane (Section 9).

Claims pending OutboxEvent records using SELECT FOR UPDATE SKIP LOCKED in short transactions,
publishes them to RabbitMQ/Celery outside the DB transaction with publisher confirms enabled,
and confirms publication in a subsequent short transaction.
"""

import asyncio
import logging
import os
import signal
import socket
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.celery_app import celery_app
from app.db.models import OutboxEvent
from app.execution.outbox_router import OutboxRouter, UnroutableEventError

logger = logging.getLogger(__name__)


def get_utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class OutboxDispatcher:
    """Outbox Dispatcher service for claiming and publishing outbox events."""

    def __init__(self, dispatcher_id: Optional[str] = None):
        hostname = socket.gethostname()
        pid = os.getpid()
        self.dispatcher_id = dispatcher_id or f"dispatcher-{hostname}-{pid}-{uuid4().hex[:6]}"
        self.running = False

    async def claim_batch(
        self,
        db: AsyncSession,
        batch_size: int = 100,
    ) -> list[OutboxEvent]:
        """Claim up to batch_size pending outbox events using SKIP LOCKED in a short transaction.
        
        Updates status to 'processing', sets locked_by, locked_at, and increments attempt_count.
        Commits before returning to release row locks quickly and ensure PgBouncer compatibility.
        """
        now_utc = get_utc_now()
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == "pending",
                OutboxEvent.next_attempt_at <= now_utc,
            )
            .order_by(OutboxEvent.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
        res = await db.execute(stmt)
        events = list(res.scalars().all())

        if not events:
            return []

        for event in events:
            event.status = "processing"
            event.locked_by = self.dispatcher_id
            event.locked_at = now_utc
            event.attempt_count += 1

        await db.commit()
        return events

    async def publish_event(
        self,
        db: AsyncSession,
        event: OutboxEvent,
    ) -> dict[str, Any]:
        """Route and publish event to Celery exchange outside DB transaction.
        
        Uses OutboxEvent.id as message_id and task_id.
        """
        routed = await OutboxRouter.route_event(db, event)

        # Publish task to RabbitMQ / Celery
        celery_app.send_task(
            routed["task_name"],
            args=routed["args"],
            kwargs=routed["kwargs"],
            queue=routed["queue"],
            task_id=str(event.id),
            message_id=str(event.id),
        )

        return routed

    async def confirm_event(
        self,
        db: AsyncSession,
        event_id: UUID,
    ) -> None:
        """Mark event as published in a short transaction."""
        now_utc = get_utc_now()
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="published",
                published_at=now_utc,
                locked_by=None,
                locked_at=None,
            )
        )
        await db.execute(stmt)
        await db.commit()

    async def handle_publish_error(
        self,
        db: AsyncSession,
        event: OutboxEvent,
        error: Exception,
    ) -> None:
        """Handle publish failures for an outbox event.
        
        - Unroutable/structural errors: transition to 'failed' with last_error.
        - Transient broker/network errors: return to 'pending' with exponential backoff.
        """
        now_utc = get_utc_now()
        error_msg = f"{type(error).__name__}: {str(error)}"

        if isinstance(error, (UnroutableEventError, ValueError, KeyError)):
            logger.error("Structurally invalid/unroutable event %s: %s", event.id, error_msg)
            stmt = (
                update(OutboxEvent)
                .where(OutboxEvent.id == event.id)
                .values(
                    status="failed",
                    last_error=error_msg,
                    locked_by=None,
                    locked_at=None,
                )
            )
        else:
            # Calculate exponential backoff for transient broker/network errors
            # 1st retry: ~1s, 2nd: ~2s, 3rd: ~4s, 4th: ~8s ... max 600s
            attempts = max(1, event.attempt_count)
            backoff_seconds = min(600, 2 ** (attempts - 1))
            next_attempt_at = now_utc + timedelta(seconds=backoff_seconds)

            logger.warning(
                "Transient publish failure for event %s (attempt %d). Rescheduling in %ds: %s",
                event.id,
                event.attempt_count,
                backoff_seconds,
                error_msg,
            )

            stmt = (
                update(OutboxEvent)
                .where(OutboxEvent.id == event.id)
                .values(
                    status="pending",
                    next_attempt_at=next_attempt_at,
                    last_error=error_msg,
                    locked_by=None,
                    locked_at=None,
                )
            )

        await db.execute(stmt)
        await db.commit()

    async def dispatch_batch(
        self,
        db_factory: async_sessionmaker[AsyncSession],
        batch_size: int = 100,
    ) -> int:
        """Process one batch of pending outbox events.
        
        Returns the count of successfully published events.
        """
        async with db_factory() as db:
            claimed_events = await self.claim_batch(db, batch_size=batch_size)

        if not claimed_events:
            return 0

        published_count = 0
        for event in claimed_events:
            try:
                # 1. Route & Publish outside DB transaction
                async with db_factory() as route_db:
                    await self.publish_event(route_db, event)

                # 2. Confirm publication in short transaction
                async with db_factory() as confirm_db:
                    await self.confirm_event(confirm_db, event.id)

                published_count += 1

            except Exception as exc:
                # 3. Handle error in short transaction
                async with db_factory() as err_db:
                    await self.handle_publish_error(err_db, event, exc)

        return published_count

    async def run_forever(
        self,
        db_factory: async_sessionmaker[AsyncSession],
        poll_interval: float = 1.0,
        batch_size: int = 100,
    ) -> None:
        """Run dispatcher daemon loop with graceful shutdown signal handling."""
        self.running = True
        logger.info("Starting OutboxDispatcher loop [dispatcher_id=%s]", self.dispatcher_id)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._handle_shutdown, sig)
            except (NotImplementedError, RuntimeError):
                # Signal handlers not supported (e.g., Windows non-main thread)
                pass

        while self.running:
            try:
                count = await self.dispatch_batch(db_factory, batch_size=batch_size)
                if count == 0:
                    await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                logger.info("OutboxDispatcher loop cancelled.")
                break
            except Exception as exc:
                logger.exception("Unexpected error in OutboxDispatcher loop: %s", exc)
                await asyncio.sleep(poll_interval)

        logger.info("OutboxDispatcher loop stopped gracefully.")

    def _handle_shutdown(self, sig: int) -> None:
        logger.info("Received shutdown signal %s. Stopping OutboxDispatcher...", sig)
        self.running = False
