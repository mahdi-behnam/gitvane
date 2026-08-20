"""Unit tests for OutboxDispatcher service."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.db.models import OutboxEvent
from app.execution.outbox_dispatcher import OutboxDispatcher
from app.execution.outbox_router import UnroutableEventError


@pytest.fixture
async def async_engine():
    """Create in-memory SQLite async engine for unit testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_factory(async_engine):
    """Create async session factory for testing."""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_claim_batch_updates_locked_fields_and_attempt_count(db_factory):
    """Verify claim_batch sets status='processing', locked_by, locked_at, and increments attempt_count."""
    now_utc = datetime.now(timezone.utc)
    event_id = uuid4()
    gen_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=gen_id,
            event_type="prepare_requested",
            payload={"generation_id": str(gen_id)},
            status="pending",
            attempt_count=0,
            next_attempt_at=now_utc - timedelta(seconds=10),
            created_at=now_utc - timedelta(seconds=10),
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher(dispatcher_id="test-dispatcher-1")

    async with db_factory() as session:
        claimed = await dispatcher.claim_batch(session, batch_size=10)

    assert len(claimed) == 1
    c_event = claimed[0]
    assert c_event.id == event_id
    assert c_event.status == "processing"
    assert c_event.locked_by == "test-dispatcher-1"
    assert c_event.locked_at is not None
    assert c_event.attempt_count == 1


@pytest.mark.asyncio
async def test_publish_event_uses_event_id_as_task_and_message_id(db_factory):
    """Verify publish_event sets Celery task_id and message_id to OutboxEvent.id."""
    event_id = uuid4()
    gen_id = uuid4()
    event = OutboxEvent(
        id=event_id,
        aggregate_id=gen_id,
        event_type="prepare_requested",
        payload={"generation_id": str(gen_id)},
        status="processing",
    )

    dispatcher = OutboxDispatcher()

    with patch("app.execution.outbox_dispatcher.celery_app.send_task") as mock_send_task:
        async with db_factory() as session:
            routed = await dispatcher.publish_event(session, event)

        mock_send_task.assert_called_once_with(
            "app.tasks.parser_tasks.task_prepare_and_parse",
            args=[str(gen_id)],
            kwargs={},
            queue="indexing_cpu",
            task_id=str(event_id),
            message_id=str(event_id),
        )
        assert routed["queue"] == "indexing_cpu"


@pytest.mark.asyncio
async def test_confirm_event_marks_published(db_factory):
    """Verify confirm_event transitions event status to 'published' and clears lock fields."""
    now_utc = datetime.now(timezone.utc)
    event_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=uuid4(),
            event_type="prepare_requested",
            payload={},
            status="processing",
            locked_by="test-disp",
            locked_at=now_utc,
            attempt_count=1,
            next_attempt_at=now_utc,
            created_at=now_utc,
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher()
    async with db_factory() as session:
        await dispatcher.confirm_event(session, event_id)

    async with db_factory() as session:
        updated = await session.get(OutboxEvent, event_id)
        assert updated.status == "published"
        assert updated.published_at is not None
        assert updated.locked_by is None
        assert updated.locked_at is None


@pytest.mark.asyncio
async def test_handle_publish_transient_error_exponential_backoff(db_factory):
    """Verify transient broker error resets event to 'pending' with exponential backoff next_attempt_at."""
    now_utc = datetime.now(timezone.utc)
    event_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=uuid4(),
            event_type="prepare_requested",
            payload={},
            status="processing",
            attempt_count=3,
            locked_by="test-disp",
            locked_at=now_utc,
            next_attempt_at=now_utc,
            created_at=now_utc,
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher()
    transient_error = ConnectionError("RabbitMQ broker connection reset")

    async with db_factory() as session:
        fresh_event = await session.get(OutboxEvent, event_id)
        await dispatcher.handle_publish_error(session, fresh_event, transient_error)

    async with db_factory() as session:
        updated = await session.get(OutboxEvent, event_id)
        assert updated.status == "pending"
        assert updated.locked_by is None
        assert updated.locked_at is None
        assert "ConnectionError: RabbitMQ broker connection reset" in updated.last_error
        next_att = updated.next_attempt_at
        if next_att.tzinfo is None:
            next_att = next_att.replace(tzinfo=timezone.utc)
        assert next_att > now_utc


@pytest.mark.asyncio
async def test_handle_publish_unroutable_error_marks_failed(db_factory):
    """Verify unroutable event transitions to 'failed' status with last_error."""
    now_utc = datetime.now(timezone.utc)
    event_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=event_id,
            aggregate_id=uuid4(),
            event_type="unknown_type",
            payload={},
            status="processing",
            attempt_count=1,
            locked_by="test-disp",
            locked_at=now_utc,
            next_attempt_at=now_utc,
            created_at=now_utc,
        )
        session.add(event)
        await session.commit()

    dispatcher = OutboxDispatcher()
    unroutable_error = UnroutableEventError("Unknown event type: unknown_type")

    async with db_factory() as session:
        fresh_event = await session.get(OutboxEvent, event_id)
        await dispatcher.handle_publish_error(session, fresh_event, unroutable_error)

    async with db_factory() as session:
        updated = await session.get(OutboxEvent, event_id)
        assert updated.status == "failed"
        assert updated.locked_by is None
        assert updated.locked_at is None
        assert "UnroutableEventError: Unknown event type: unknown_type" in updated.last_error
