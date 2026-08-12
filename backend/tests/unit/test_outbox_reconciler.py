"""Unit tests for OutboxReconciler service (Section 10 spec)."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.db.models import EmbeddingBatch, IndexGeneration, OutboxEvent, Repository, User
from app.execution.outbox_reconciler import OutboxReconciler


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
async def test_recover_expired_outbox_leases(db_factory):
    """Verify expired outbox processing lease resets from processing -> pending."""
    now_utc = datetime.now(timezone.utc)
    stale_lock_time = now_utc - timedelta(seconds=600)  # 10m ago > 300s timeout

    async with db_factory() as session:
        event = OutboxEvent(
            id=uuid4(),
            aggregate_id=uuid4(),
            event_type="prepare_requested",
            payload={},
            status="processing",
            locked_by="dead-dispatcher",
            locked_at=stale_lock_time,
            created_at=stale_lock_time,
            next_attempt_at=stale_lock_time,
        )
        session.add(event)
        await session.commit()
        event_id = event.id

    reconciler = OutboxReconciler()
    async with db_factory() as session:
        count = await reconciler.recover_expired_outbox_leases(session, lease_timeout_seconds=300)

    assert count == 1
    async with db_factory() as session:
        recovered = await session.get(OutboxEvent, event_id)
        assert recovered.status == "pending"
        assert recovered.locked_by is None
        assert recovered.locked_at is None


@pytest.mark.asyncio
async def test_recover_expired_parser_leases(db_factory):
    """Verify expired parser lease recovers desired generation to queued + prepare_requested outbox event."""
    now_utc = datetime.now(timezone.utc)
    expired_lease_time = now_utc - timedelta(minutes=5)
    repo_id = uuid4()
    gen_id = uuid4()

    async with db_factory() as session:
        user = User(id=1, email="test@example.com", full_name="Test User")
        session.add(user)
        await session.flush()

        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="bge-small",
            embedding_dimension=384,
            embedding_config_hash="hash123",
            status="parsing",
            stage_lease_owner="crashed-worker-1",
            stage_lease_expires_at=expired_lease_time,
            stage_attempt=1,
            created_at=now_utc - timedelta(hours=1),
            updated_at=expired_lease_time,
        )
        repo = Repository(
            id=repo_id,
            name="test-repo",
            clone_url="https://github.com/org/repo.git",
            owner_id=1,
            desired_generation_id=gen_id,
        )
        session.add_all([gen, repo])
        await session.commit()

    reconciler = OutboxReconciler()
    async with db_factory() as session:
        count = await reconciler.recover_expired_parser_leases(session)

    assert count == 1
    async with db_factory() as session:
        gen_after = await session.get(IndexGeneration, gen_id)
        assert gen_after.status == "queued"
        assert gen_after.stage_lease_owner is None
        assert gen_after.stage_lease_expires_at is None

        # Check prepare_requested outbox event was created
        events_res = await session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == gen_id,
                OutboxEvent.event_type == "prepare_requested",
            )
        )
        events = list(events_res.scalars().all())
        assert len(events) == 1
        assert events[0].status == "pending"


@pytest.mark.asyncio
async def test_recover_expired_embedding_batch_leases(db_factory):
    """Verify expired embedding batch lease recovers batch to pending + embedding_batch_requested event."""
    now_utc = datetime.now(timezone.utc)
    expired_lease_time = now_utc - timedelta(minutes=5)
    repo_id = uuid4()
    gen_id = uuid4()
    batch_id = uuid4()

    async with db_factory() as session:
        user = User(id=2, email="user2@example.com", full_name="User 2")
        session.add(user)
        await session.flush()

        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="nim",
            embedding_model="nv-embed",
            embedding_dimension=1024,
            embedding_config_hash="hash456",
            status="embedding",
            created_at=now_utc - timedelta(hours=1),
            updated_at=now_utc,
        )
        repo = Repository(
            id=repo_id,
            name="test-repo-2",
            clone_url="https://github.com/org/repo2.git",
            owner_id=2,
            desired_generation_id=gen_id,
        )
        batch = EmbeddingBatch(
            id=batch_id,
            generation_id=gen_id,
            batch_index=3,
            status="processing",
            chunk_start_id=10,
            chunk_end_id=20,
            lease_owner="crashed-gpu-worker",
            lease_expires_at=expired_lease_time,
            attempt_count=1,
        )
        session.add_all([gen, repo, batch])
        await session.commit()

    reconciler = OutboxReconciler()
    async with db_factory() as session:
        count = await reconciler.recover_expired_embedding_batch_leases(session)

    assert count == 1
    async with db_factory() as session:
        batch_after = await session.get(EmbeddingBatch, batch_id)
        assert batch_after.status == "pending"
        assert batch_after.lease_owner is None
        assert batch_after.lease_expires_at is None

        # Check embedding_batch_requested event created
        events_res = await session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == gen_id,
                OutboxEvent.event_type == "embedding_batch_requested",
            )
        )
        events = list(events_res.scalars().all())
        assert len(events) == 1
        assert events[0].payload["batch_index"] == 3
        assert events[0].payload["embedding_backend"] == "nim"


@pytest.mark.asyncio
async def test_recover_stuck_finalizing_generations(db_factory):
    """Verify desired generation stuck in finalizing beyond threshold receives safety activation event."""
    now_utc = datetime.now(timezone.utc)
    stuck_time = now_utc - timedelta(seconds=200)  # 200s > 120s threshold
    repo_id = uuid4()
    gen_id = uuid4()

    async with db_factory() as session:
        user = User(id=3, email="user3@example.com", full_name="User 3")
        session.add(user)
        await session.flush()

        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="bge-small",
            embedding_dimension=384,
            embedding_config_hash="hash789",
            status="finalizing",
            created_at=stuck_time - timedelta(minutes=10),
            updated_at=stuck_time,
        )
        repo = Repository(
            id=repo_id,
            name="test-repo-3",
            clone_url="https://github.com/org/repo3.git",
            owner_id=3,
            desired_generation_id=gen_id,
        )
        session.add_all([gen, repo])
        await session.commit()

    reconciler = OutboxReconciler()
    async with db_factory() as session:
        count = await reconciler.recover_stuck_finalizing_generations(session, threshold_seconds=120)

    assert count == 1
    async with db_factory() as session:
        events_res = await session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == gen_id,
                OutboxEvent.event_type == "activation_requested",
            )
        )
        events = list(events_res.scalars().all())
        assert len(events) == 1
        assert events[0].status == "pending"
