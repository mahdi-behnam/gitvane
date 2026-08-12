from datetime import datetime, timezone
import uuid

import pytest
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


def test_repository_generation_fields():
    active_id = uuid.uuid4()
    desired_id = uuid.uuid4()
    repo = Repository(
        name="test-repo",
        clone_url="https://github.com/example/test-repo.git",
        owner_id=1,
        active_generation_id=active_id,
        desired_generation_id=desired_id,
    )

    assert repo.active_generation_id == active_id
    assert repo.desired_generation_id == desired_id


def test_index_generation_model_instantiation():
    repo_id = uuid.uuid4()
    gen_id = uuid.uuid4()
    gen = IndexGeneration(
        id=gen_id,
        repository_id=repo_id,
        requested_ref="main",
        commit_sha="a1b2c3d4e5f67890123456789012345678901234",
        pipeline_version="1.0.0",
        parser_version="1.0.0",
        chunker_version="1.0.0",
        embedding_backend="local",
        embedding_model="jinaai/jina-embeddings-v2-base-code",
        embedding_dimension=768,
        embedding_config_hash="abc123hash",
        status="queued",
        stage_attempt=0,
    )

    assert gen.id == gen_id
    assert gen.repository_id == repo_id
    assert gen.requested_ref == "main"
    assert gen.status == "queued"
    assert gen.stage_attempt == 0
    assert gen.commit_sha == "a1b2c3d4e5f67890123456789012345678901234"


def test_embedding_batch_model_instantiation():
    gen_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    batch = EmbeddingBatch(
        id=batch_id,
        generation_id=gen_id,
        batch_index=0,
        status="pending",
        chunk_start_id=1,
        chunk_end_id=50,
        attempt_count=0,
    )

    assert batch.id == batch_id
    assert batch.generation_id == gen_id
    assert batch.batch_index == 0
    assert batch.status == "pending"
    assert batch.chunk_start_id == 1
    assert batch.chunk_end_id == 50


def test_outbox_event_model_instantiation():
    event_id = uuid.uuid4()
    aggregate_id = uuid.uuid4()
    payload = {"generation_id": str(aggregate_id), "ref": "main"}
    event = OutboxEvent(
        id=event_id,
        aggregate_id=aggregate_id,
        event_type="prepare_requested",
        payload=payload,
        status="pending",
        attempt_count=0,
    )

    assert event.id == event_id
    assert event.aggregate_id == aggregate_id
    assert event.event_type == "prepare_requested"
    assert event.payload == payload
    assert event.status == "pending"
    assert event.attempt_count == 0


def test_generation_scoped_models_attributes():
    gen_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    code_file = CodeFile(
        repository_id=repo_id,
        generation_id=gen_id,
        path="src/main.py",
        language="python",
        content_hash="hash123",
        loc=42,
    )
    assert code_file.generation_id == gen_id

    symbol = Symbol(
        repository_id=repo_id,
        generation_id=gen_id,
        file_id=1,
        qualified_name="src.main.app",
        simple_name="app",
        symbol_type="function",
        start_line=1,
        end_line=10,
        content_hash="hash456",
    )
    assert symbol.generation_id == gen_id

    dep_edge = DependencyEdge(
        repository_id=repo_id,
        generation_id=gen_id,
        source_file_id=1,
        target_file_id=2,
        edge_type="import",
    )
    assert dep_edge.generation_id == gen_id

    chunk = CodeChunk(
        repository_id=repo_id,
        generation_id=gen_id,
        file_id=1,
        chunk_type="function",
        text="def main(): pass",
        start_line=1,
        end_line=2,
        content_hash="hash789",
    )
    assert chunk.generation_id == gen_id

    embedding = CodeEmbedding(
        generation_id=gen_id,
        chunk_id=1,
        provider="local",
        model="jina-embeddings-v2-base-code",
        dimensions=768,
        embedding=[0.1] * 768,
    )
    assert embedding.generation_id == gen_id


def test_index_generation_allowed_statuses():
    allowed = {
        "queued",
        "preparing",
        "parsing",
        "embedding",
        "finalizing",
        "completed",
        "failed",
        "cancelled",
        "superseded",
    }
    table_args = IndexGeneration.__table_args__
    check_constraints = [
        arg for arg in table_args if hasattr(arg, "name") and arg.name == "ck_index_generations_status"
    ]
    assert len(check_constraints) == 1
    sqltext = str(check_constraints[0].sqltext)
    for st in allowed:
        assert st in sqltext


def test_outbox_event_allowed_statuses():
    allowed = {"pending", "processing", "published", "failed"}
    table_args = OutboxEvent.__table_args__
    check_constraints = [
        arg for arg in table_args if hasattr(arg, "name") and arg.name == "ck_outbox_events_status"
    ]
    assert len(check_constraints) == 1
    sqltext = str(check_constraints[0].sqltext)
    for st in allowed:
        assert st in sqltext


def test_embedding_batch_allowed_statuses():
    allowed = {"pending", "processing", "completed", "failed"}
    table_args = EmbeddingBatch.__table_args__
    check_constraints = [
        arg for arg in table_args if hasattr(arg, "name") and arg.name == "ck_embedding_batches_status"
    ]
    assert len(check_constraints) == 1
    sqltext = str(check_constraints[0].sqltext)
    for st in allowed:
        assert st in sqltext
