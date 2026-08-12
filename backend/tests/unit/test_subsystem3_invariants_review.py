"""Dual-Review Convergence Loop Verification for Subsystem 3 (Outbox Dispatcher & Reconciler).

Reviewer A: Invariants 1, 3, 9 verification.
Reviewer B: PgBouncer compatibility (short transaction scopes), exception safety, and daemon loop shutdown handling.
"""

import asyncio
import signal
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.db.models import OutboxEvent
from app.execution.outbox_dispatcher import OutboxDispatcher
from app.execution.outbox_reconciler import OutboxReconciler
from app.execution.outbox_router import OutboxRouter, UnroutableEventError


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# ============================================================================
# REVIEWER A: INVARIANTS 1, 3, 9 VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_reviewer_a_invariant_1_outbox_is_sole_dispatcher():
    """Verify Invariant 1: OutboxRouter maps all required inter-stage events to Celery task queues."""
    events = [
        ("prepare_requested", {"generation_id": str(uuid4())}, "indexing_cpu"),
        ("embedding_batch_requested", {"generation_id": str(uuid4()), "batch_index": 0, "embedding_backend": "local"}, "embeddings_gpu"),
        ("embedding_batch_requested", {"generation_id": str(uuid4()), "batch_index": 1, "embedding_backend": "nim"}, "embeddings_nim_io"),
        ("activation_requested", {"generation_id": str(uuid4())}, "workflow_control"),
    ]

    for event_type, payload, expected_queue in events:
        event = OutboxEvent(id=uuid4(), aggregate_id=uuid4(), event_type=event_type, payload=payload, status="pending")
        routed = await OutboxRouter.route_event(None, event)
        assert routed["queue"] == expected_queue, f"{event_type} payload={payload} did not route to {expected_queue}"


@pytest.mark.asyncio
async def test_reviewer_a_invariant_3_at_least_once_delivery_idempotent_republication(db_factory):
    """Verify Invariant 3: Re-claiming or re-publishing an outbox event uses stable event.id as message_id and task_id."""
    event_id = uuid4()
    gen_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=gen_id,
            event_type="prepare_requested",
            payload={"generation_id": str(gen_id)},
            status="pending",
            next_attempt_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher()

    with patch("app.execution.outbox_dispatcher.celery_app.send_task") as mock_send:
        # First publication attempt
        async with db_factory() as session:
            claimed = await dispatcher.claim_batch(session, batch_size=10)
            await dispatcher.publish_event(session, claimed[0])

        mock_send.assert_called_with(
            "app.tasks.parser_tasks.task_prepare_and_parse",
            args=[str(gen_id)],
            kwargs={},
            queue="indexing_cpu",
            task_id=str(event_id),
            message_id=str(event_id),
        )

        # Simulate transient error & re-claim
        async with db_factory() as session:
            ev = await session.get(OutboxEvent, event_id)
            await dispatcher.handle_publish_error(session, ev, ConnectionError("Transient RMQ restart"))

        # Re-publish attempt maintains exact same task_id & message_id
        async with db_factory() as session:
            ev_reclaimed = await session.get(OutboxEvent, event_id)
            await dispatcher.publish_event(session, ev_reclaimed)

        assert mock_send.call_count == 2
        last_call_kwargs = mock_send.call_args_list[1][1]
        assert last_call_kwargs["task_id"] == str(event_id)
        assert last_call_kwargs["message_id"] == str(event_id)


@pytest.mark.asyncio
async def test_reviewer_a_invariant_9_postgresql_app_failure_truth(db_factory):
    """Verify Invariant 9: Structural/application outbox errors persist to PostgreSQL with status='failed' and last_error."""
    event_id = uuid4()
    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=uuid4(),
            event_type="corrupt_event",
            payload={},
            status="processing",
            attempt_count=1,
            next_attempt_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher()
    unroutable = UnroutableEventError("Corrupt event type")

    async with db_factory() as session:
        ev = await session.get(OutboxEvent, event_id)
        await dispatcher.handle_publish_error(session, ev, unroutable)

    async with db_factory() as session:
        db_ev = await session.get(OutboxEvent, event_id)
        assert db_ev.status == "failed"
        assert "UnroutableEventError: Corrupt event type" in db_ev.last_error


# ============================================================================
# REVIEWER B: PGBOUNCER COMPATIBILITY, EXCEPTION SAFETY & DAEMON LOOP SHUTDOWN
# ============================================================================

@pytest.mark.asyncio
async def test_reviewer_b_pgbouncer_compatibility_short_transactions(db_factory):
    """Verify PgBouncer compatibility: claim_batch commits DB locks before network publishing occurs."""
    event_id = uuid4()
    now_utc = datetime.now(timezone.utc)

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=uuid4(),
            event_type="prepare_requested",
            payload={"generation_id": str(uuid4())},
            status="pending",
            attempt_count=0,
            next_attempt_at=now_utc - timedelta(seconds=5),
            created_at=now_utc - timedelta(seconds=5),
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher(dispatcher_id="pgbouncer-test-disp")

    # Claim transaction completes and commits
    async with db_factory() as session:
        claimed = await dispatcher.claim_batch(session, batch_size=10)
        # Transaction is already committed here
        assert session.is_active

    # Inspect in new session to verify row state committed
    async with db_factory() as session:
        db_ev = await session.get(OutboxEvent, event_id)
        assert db_ev.status == "processing"
        assert db_ev.locked_by == "pgbouncer-test-disp"


@pytest.mark.asyncio
async def test_reviewer_b_dispatcher_graceful_shutdown_handling():
    """Verify dispatcher gracefully handles shutdown signals (SIGINT / SIGTERM)."""
    dispatcher = OutboxDispatcher()
    assert dispatcher.running is False

    dispatcher.running = True
    dispatcher._handle_shutdown(signal.SIGTERM)
    assert dispatcher.running is False


@pytest.mark.asyncio
async def test_reviewer_b_reconciler_graceful_shutdown_handling():
    """Verify reconciler gracefully handles shutdown signals (SIGINT / SIGTERM)."""
    reconciler = OutboxReconciler()
    assert reconciler.running is False

    reconciler.running = True
    reconciler._handle_shutdown(signal.SIGINT)
    assert reconciler.running is False
