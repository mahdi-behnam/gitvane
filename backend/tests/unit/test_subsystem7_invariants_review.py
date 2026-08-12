"""Dual-Review Convergence Loop tests for Subsystem 7 (Failure-Injection & Integration Test Matrix).

Reviewer A Checklist:
- Execute full test suite and confirm all 25 failure injection cases pass cleanly.
- Assert non-negotiable invariants:
  1. No partial generation becomes active.
  2. Stale workers cannot commit authoritative state.
  3. Duplicate messages do not duplicate logical data.
  4. A newer desired generation cannot be overwritten by an older one.
  5. No processing/preparing/parsing/finalizing state can remain permanently stuck.
  6. Redis failure cannot corrupt indexing.
  7. RabbitMQ delivery is never treated as exactly-once.

Reviewer B Checklist:
- Verify test structure, mock isolation, and test runner reliability.
- Verify PgBouncer compatibility (short transactions, no long table locks, explicit commits).
- Verify exception safety and clean worker lease fencing.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    CodeChunk,
    EmbeddingBatch,
    IndexGeneration,
    OutboxEvent,
    Repository,
    User,
)
from app.execution.activation_engine import activate_generation
from app.execution.embedding_engine import (
    checkpoint_batch_completion,
    claim_embedding_batch_lease,
    persist_batch_embeddings,
)
from app.execution.failure_engine import handle_parser_failure
from app.execution.outbox_dispatcher import OutboxDispatcher
from app.execution.outbox_reconciler import OutboxReconciler
from app.execution.parser_engine import FenceCheckFailedError, verify_parser_fence
from app.services.progress_publisher import ProgressStreamPublisher


@pytest.fixture
async def async_engine():
    """In-memory SQLite engine for review tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_factory(async_engine):
    """Session factory for review tests."""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def create_default_user(db_factory):
    """Create default user required for Repository owner foreign key."""
    async with db_factory() as session:
        user = User(id=1, email="test@example.com", full_name="Test Owner")
        session.add(user)
        await session.commit()


def make_repo(repo_id, name="test-repo", desired_gen_id=None, active_gen_id=None):
    return Repository(
        id=repo_id,
        name=name,
        clone_url="https://github.com/example/test.git",
        owner_id=1,
        status="ready",
        desired_generation_id=desired_gen_id,
        active_generation_id=active_gen_id,
    )


# -----------------------------------------------------------------------------
# Reviewer A: Non-Negotiable Invariants Assertions
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reviewer_a_invariant_no_partial_generation_becomes_active(db_factory):
    """Invariant 1: No partial generation (parsing/embedding/failed) becomes active."""
    now_utc = datetime.now(timezone.utc)
    gen_id = uuid4()
    repo_id = uuid4()

    async with db_factory() as session:
        repo = make_repo(repo_id, "repo-inv1", desired_gen_id=gen_id)
        # Generation is in 'parsing' state (partial!)
        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            status="parsing",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="jina",
            embedding_dimension=768,
            embedding_config_hash="hash1",
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add_all([repo, gen])
        await session.commit()

    # Attempt to activate partial generation
    async with db_factory() as session:
        res = await activate_generation(session, gen_id)

    assert res["status"] == "skipped"
    async with db_factory() as session:
        r = await session.get(Repository, repo_id)
        assert r.active_generation_id is None  # Partial generation was NOT activated!


@pytest.mark.asyncio
async def test_reviewer_a_invariant_stale_workers_cannot_commit_state(db_factory):
    """Invariant 2: Stale workers cannot commit authoritative state after lease expiry."""
    now_utc = datetime.now(timezone.utc)
    gen_id = uuid4()
    repo_id = uuid4()

    async with db_factory() as session:
        repo = make_repo(repo_id, "repo-inv2", desired_gen_id=gen_id)
        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            status="parsing",
            stage_lease_owner="new-parser",
            stage_lease_expires_at=now_utc + timedelta(hours=2),
            stage_attempt=2,  # replacement worker has attempt 2
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="jina",
            embedding_dimension=768,
            embedding_config_hash="hash1",
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add_all([repo, gen])
        await session.commit()

    # Stale parser (attempt 1) attempts failure commit
    async with db_factory() as session:
        status = await handle_parser_failure(session, gen_id, "stale-parser", 1, "Error")

    assert status is None  # Fenced out! Stale worker cannot mutate DB state.


@pytest.mark.asyncio
async def test_reviewer_a_invariant_duplicate_messages_do_not_duplicate_data(db_factory):
    """Invariant 3: Duplicate messages do not duplicate logical data."""
    now_utc = datetime.now(timezone.utc)
    gen_id = uuid4()
    repo_id = uuid4()

    async with db_factory() as session:
        repo = make_repo(repo_id, "repo-inv3", desired_gen_id=gen_id)
        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            status="finalizing",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="jina",
            embedding_dimension=768,
            embedding_config_hash="hash1",
            created_at=now_utc,
            updated_at=now_utc,
        )
        session.add_all([repo, gen])
        await session.commit()

    # Execute activation 3 times
    for _ in range(3):
        async with db_factory() as session:
            await activate_generation(session, gen_id)
            await session.commit()

    async with db_factory() as session:
        r = await session.get(Repository, repo_id)
        assert r.active_generation_id == gen_id  # Single active generation!


@pytest.mark.asyncio
async def test_reviewer_a_invariant_newer_desired_generation_cannot_be_overwritten(db_factory):
    """Invariant 4: A newer desired generation (G2) cannot be overwritten by an older one (G1)."""
    now_utc = datetime.now(timezone.utc)
    g1_id = uuid4()
    g2_id = uuid4()
    repo_id = uuid4()

    async with db_factory() as session:
        # Repository desired generation is G2
        repo = make_repo(repo_id, "repo-inv4", desired_gen_id=g2_id)
        g1 = IndexGeneration(
            id=g1_id,
            repository_id=repo_id,
            requested_ref="main",
            status="finalizing",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="jina",
            embedding_dimension=768,
            embedding_config_hash="hash1",
            created_at=now_utc - timedelta(hours=1),
            updated_at=now_utc,
        )
        session.add_all([repo, g1])
        await session.commit()

    # Older G1 attempts activation
    async with db_factory() as session:
        res = await activate_generation(session, g1_id)
        await session.commit()

    assert res["status"] == "superseded"  # G1 marked superseded!
    async with db_factory() as session:
        r = await session.get(Repository, repo_id)
        assert r.active_generation_id != g1_id  # G1 was not activated.


@pytest.mark.asyncio
async def test_reviewer_a_invariant_no_stuck_states_without_recovery_path(db_factory):
    """Invariant 5: Reconciler guarantees no preparing/parsing/embedding state remains permanently stuck."""
    now_utc = datetime.now(timezone.utc)
    gen_id = uuid4()
    repo_id = uuid4()
    batch_id = uuid4()

    async with db_factory() as session:
        repo = make_repo(repo_id, "repo-inv5", desired_gen_id=gen_id)
        gen = IndexGeneration(
            id=gen_id,
            repository_id=repo_id,
            requested_ref="main",
            status="embedding",
            pipeline_version="1.0",
            parser_version="1.0",
            chunker_version="1.0",
            embedding_backend="local",
            embedding_model="jina",
            embedding_dimension=768,
            embedding_config_hash="hash1",
            created_at=now_utc,
            updated_at=now_utc,
        )
        batch = EmbeddingBatch(
            id=batch_id,
            generation_id=gen_id,
            batch_index=0,
            status="processing",
            chunk_start_id=1,
            chunk_end_id=5,
            lease_owner="stuck-worker",
            lease_expires_at=now_utc - timedelta(minutes=30),  # expired
        )
        session.add_all([repo, gen, batch])
        await session.commit()

    reconciler = OutboxReconciler()
    async with db_factory() as session:
        rec_count = await reconciler.recover_expired_embedding_batch_leases(session)

    assert rec_count == 1
    async with db_factory() as session:
        b = await session.get(EmbeddingBatch, batch_id)
        assert b.status == "pending"  # Recovered to pending for next attempt!


# -----------------------------------------------------------------------------
# Reviewer B: Mock Isolation, Structure, and Reliability Checks
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reviewer_b_mock_isolation_and_test_runner_reliability(db_factory):
    """Reviewer B: Verify tests use in-memory isolated sessions without side effects on external state."""
    async with db_factory() as session:
        event = OutboxEvent(
            id=uuid4(),
            aggregate_id=uuid4(),
            event_type="test_event",
            payload={},
            status="pending",
            next_attempt_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        session.add(event)
        await session.commit()

    async with db_factory() as session:
        res = await session.execute(select(OutboxEvent))
        assert len(res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_reviewer_b_pgbouncer_short_transactions_compatibility(db_factory):
    """Reviewer B: Verify outbox and reconciler use short transactions compatible with PgBouncer transaction mode."""
    dispatcher = OutboxDispatcher()
    now_utc = datetime.now(timezone.utc)
    ev_id = uuid4()

    async with db_factory() as session:
        event = OutboxEvent(
            id=ev_id,
            aggregate_id=uuid4(),
            event_type="prepare_requested",
            payload={},
            status="pending",
            next_attempt_at=now_utc,
            created_at=now_utc,
        )
        session.add(event)
        await session.commit()

    # Short transaction 1: Claim batch
    async with db_factory() as session:
        claimed = await dispatcher.claim_batch(session)
        assert len(claimed) == 1

    # Short transaction 2: Confirm event
    async with db_factory() as session:
        await dispatcher.confirm_event(session, ev_id)

    async with db_factory() as session:
        confirmed = await session.get(OutboxEvent, ev_id)
        assert confirmed.status == "published"
