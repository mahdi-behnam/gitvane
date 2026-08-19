import inspect
import uuid
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Index, UniqueConstraint

from app.db.models import (
    CodeChunk,
    CodeEmbedding,
    CodeFile,
    DependencyEdge,
    EmbeddingBatch,
    IndexGeneration,
    OutboxEvent,
    Repository,
    Symbol,
)


def test_invariant_2_postgresql_workflow_truth_schema():
    """Verify Invariant 2: PostgreSQL owns workflow truth via authoritative tables and fields."""
    gen_fields = {c.name for c in IndexGeneration.__table__.columns}
    required_gen_fields = {
        "id",
        "repository_id",
        "requested_ref",
        "commit_sha",
        "pipeline_version",
        "parser_version",
        "chunker_version",
        "embedding_backend",
        "embedding_model",
        "embedding_dimension",
        "embedding_config_hash",
        "status",
        "stage_lease_owner",
        "stage_lease_expires_at",
        "stage_attempt",
        "error_message",
        "created_at",
        "updated_at",
        "completed_at",
        "terminal_at",
    }
    assert required_gen_fields.issubset(gen_fields)

    batch_fields = {c.name for c in EmbeddingBatch.__table__.columns}
    required_batch_fields = {
        "id",
        "generation_id",
        "batch_index",
        "status",
        "chunk_start_id",
        "chunk_end_id",
        "lease_owner",
        "lease_expires_at",
        "attempt_count",
        "started_at",
        "completed_at",
        "last_error",
    }
    assert required_batch_fields.issubset(batch_fields)

    outbox_fields = {c.name for c in OutboxEvent.__table__.columns}
    required_outbox_fields = {
        "id",
        "aggregate_id",
        "event_type",
        "payload",
        "status",
        "attempt_count",
        "next_attempt_at",
        "locked_at",
        "locked_by",
        "created_at",
        "published_at",
        "last_error",
    }
    assert required_outbox_fields.issubset(outbox_fields)


def test_invariant_8_generation_immutability_fields():
    """Verify Invariant 8: Repository revision and embedding config fields are present in IndexGeneration."""
    immutable_fields = [
        "commit_sha",
        "pipeline_version",
        "parser_version",
        "chunker_version",
        "embedding_backend",
        "embedding_model",
        "embedding_dimension",
        "embedding_config_hash",
    ]
    for field in immutable_fields:
        assert hasattr(IndexGeneration, field), f"IndexGeneration missing immutable field: {field}"


def test_invariant_10_ephemeral_redis_progress_containment():
    """Verify Invariant 10: PostgreSQL schema maintains complete lifecycle state independent of Redis."""
    status_col = IndexGeneration.__table__.columns["status"]
    assert status_col.nullable is False

    lease_owner_col = IndexGeneration.__table__.columns["stage_lease_owner"]
    lease_expires_col = IndexGeneration.__table__.columns["stage_lease_expires_at"]
    attempt_col = IndexGeneration.__table__.columns["stage_attempt"]

    assert lease_owner_col is not None
    assert lease_expires_col is not None
    assert attempt_col is not None


def test_generation_scoping_on_graph_vector_tables():
    """Verify all generation-scoped tables have generation_id and required indexes/constraints."""
    scoped_tables = [CodeFile, Symbol, DependencyEdge, CodeChunk, CodeEmbedding]

    for model in scoped_tables:
        cols = {c.name for c in model.__table__.columns}
        assert "generation_id" in cols, f"{model.__name__} missing generation_id column"

    # Check unique constraint on CodeEmbedding (generation_id, chunk_id, model)
    embedding_uniques = [
        c for c in CodeEmbedding.__table_args__
        if isinstance(c, UniqueConstraint) and c.name == "uq_code_embeddings_gen_chunk_model"
    ]
    assert len(embedding_uniques) == 1
    unq_cols = {col.name if hasattr(col, "name") else col for col in embedding_uniques[0].columns}
    assert unq_cols == {"generation_id", "chunk_id", "model"}

    # Check unique constraint on EmbeddingBatch (generation_id, batch_index)
    batch_uniques = [
        c for c in EmbeddingBatch.__table_args__
        if isinstance(c, UniqueConstraint) and c.name == "uq_embedding_batches_gen_index"
    ]
    assert len(batch_uniques) == 1
    batch_unq_cols = {col.name if hasattr(col, "name") else col for col in batch_uniques[0].columns}
    assert batch_unq_cols == {"generation_id", "batch_index"}


def test_outbox_pending_partial_index():
    """Verify outbox pending events covering/partial index definition."""
    indexes = [
        arg for arg in OutboxEvent.__table_args__
        if isinstance(arg, Index) and arg.name == "idx_outbox_events_pending"
    ]
    assert len(indexes) == 1
    index = indexes[0]
    col_names = [col.name if hasattr(col, "name") else str(col) for col in index.columns]
    assert col_names == ["next_attempt_at", "created_at"]
    assert "status = 'pending'" in str(index.dialect_options.get("postgresql", {}).get("where", ""))


def test_alembic_migration_file_exists_and_valid():
    """Verify Alembic migration script exists and defines revision tree correctly."""
    from alembic.script import ScriptDirectory
    import os

    alembic_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "alembic")
    config = Config()
    config.set_main_option("script_location", alembic_dir)
    script = ScriptDirectory.from_config(config)

    head_revision = script.get_current_head()
    assert head_revision == "add_perf_and_vector_indexes"

    rev = script.get_revision("decoupled_outbox_schema")
    assert rev is not None
    assert rev.down_revision == "6ec32e4180bd"
