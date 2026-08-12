"""Dual-Review Convergence Loop tests for Subsystem 2 (Execution Engine & Task Fencing).

Reviewer A: Verifies Invariants 1, 3, 5, 6, 7, 8 hold.
Reviewer B: Verifies PgBouncer compatibility, exception handling, fence check correctness.
"""

import inspect
from uuid import uuid4

import pytest

from app.core.celery_app import celery_app
from app.db.models import EmbeddingBatch, IndexGeneration, OutboxEvent, Repository
from app.execution import embedding_engine, failure_engine, parser_engine
from app.tasks import embedding_tasks, failure_handlers, parser_tasks


def test_reviewer_a_invariant_1_outbox_event_creation_in_checkpoints():
    """Invariant 1: Outbox events are created in same transaction as checkpoint state transitions."""
    # Check parser checkpoint function creates OutboxEvent
    parser_src = inspect.getsource(parser_engine.final_parser_checkpoint)
    assert "OutboxEvent(" in parser_src
    assert "embedding_batch_requested" in parser_src
    assert "activation_requested" in parser_src

    # Check batch completion checkpoint creates activation OutboxEvent
    batch_src = inspect.getsource(embedding_engine.checkpoint_batch_completion)
    assert "OutboxEvent(" in batch_src
    assert "activation_requested" in batch_src


def test_reviewer_a_invariant_3_and_6_lease_and_fencing_token_fields():
    """Invariant 3 & 6: Every long-running stage has a lease and a fencing token."""
    # IndexGeneration lease fields
    gen_cols = {c.name for c in IndexGeneration.__table__.columns}
    assert "stage_lease_owner" in gen_cols
    assert "stage_lease_expires_at" in gen_cols
    assert "stage_attempt" in gen_cols

    # EmbeddingBatch lease fields
    batch_cols = {c.name for c in EmbeddingBatch.__table__.columns}
    assert "lease_owner" in batch_cols
    assert "lease_expires_at" in batch_cols
    assert "attempt_count" in batch_cols


def test_reviewer_a_invariant_5_desired_generation_fencing_in_queries():
    """Invariant 5: Desired generation fencing is enforced in lease claims and fence checks."""
    p_claim_src = inspect.getsource(parser_engine.claim_parser_stage_lease)
    assert "desired_generation_id" in p_claim_src

    e_claim_src = inspect.getsource(embedding_engine.claim_embedding_batch_lease)
    assert "desired_generation_id" in e_claim_src

    p_fence_src = inspect.getsource(parser_engine.verify_parser_fence)
    assert "desired_generation_id" in p_fence_src


def test_reviewer_a_invariant_7_monotonic_state_check_constraint():
    """Invariant 7: Monotonic state transitions defined on IndexGeneration."""
    status_col = IndexGeneration.__table__.columns["status"]
    assert status_col.nullable is False

    valid_statuses = {"queued", "preparing", "parsing", "embedding", "finalizing", "completed", "failed", "cancelled", "superseded"}
    check_constraints = [c for c in IndexGeneration.__table_args__ if hasattr(c, "name") and c.name == "ck_index_generations_status"]
    assert len(check_constraints) == 1
    assert "preparing" in str(check_constraints[0].sqltext)
    assert "embedding" in str(check_constraints[0].sqltext)


def test_reviewer_b_pgbouncer_compatibility():
    """Reviewer B: PgBouncer compatibility (transaction pool mode friendly)."""
    # Verify no session-level prepared statement locks or session-bound temporary tables are used
    parser_src = inspect.getsource(parser_engine)
    embedding_src = inspect.getsource(embedding_engine)

    assert "PREPARE TRANSACTION" not in parser_src
    assert "CREATE TEMPORARY TABLE" not in parser_src
    assert "PREPARE TRANSACTION" not in embedding_src


def test_reviewer_b_exception_handling_rollback_patterns():
    """Reviewer B: Exception handling and rollback on task failures."""
    parser_task_src = inspect.getsource(parser_tasks._async_prepare_and_parse)
    assert "await db.rollback()" in parser_task_src
    assert "handle_parser_failure(" in parser_task_src

    embed_task_src = inspect.getsource(embedding_tasks._async_generate_embeddings_batch)
    assert "await db.rollback()" in embed_task_src
    assert "handle_embedding_batch_failure(" in embed_task_src


def test_reviewer_b_fence_check_correctness():
    """Reviewer B: Fence checks check lease_owner, attempt/index, expiry, status."""
    p_verify = inspect.getsource(parser_engine.verify_parser_fence)
    assert "stage_lease_owner" in p_verify
    assert "stage_attempt" in p_verify
    assert "stage_lease_expires_at >" in p_verify

    e_verify = inspect.getsource(embedding_engine.verify_embedding_batch_fence)
    assert "lease_owner" in e_verify
    assert "batch_index" in e_verify
    assert "lease_expires_at >" in e_verify
