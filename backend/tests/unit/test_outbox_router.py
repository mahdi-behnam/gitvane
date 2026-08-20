"""Unit tests for OutboxRouter."""

from uuid import uuid4
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.db.models import OutboxEvent, IndexGeneration
from app.execution.outbox_router import OutboxRouter, UnroutableEventError


@pytest.mark.asyncio
async def test_route_prepare_requested():
    """Verify prepare_requested routes to indexing_cpu queue and task_prepare_and_parse."""
    gen_id = uuid4()
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=gen_id,
        event_type="prepare_requested",
        payload={"generation_id": str(gen_id)},
        status="pending",
    )

    routed = await OutboxRouter.route_event(None, event)

    assert routed["queue"] == "indexing_cpu"
    assert routed["task_name"] == "app.tasks.parser_tasks.task_prepare_and_parse"
    assert routed["args"] == [str(gen_id)]
    assert routed["kwargs"] == {}


@pytest.mark.asyncio
async def test_route_embedding_batch_requested_local():
    """Verify embedding_batch_requested with backend=local routes to embeddings_gpu queue."""
    gen_id = uuid4()
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=gen_id,
        event_type="embedding_batch_requested",
        payload={
            "generation_id": str(gen_id),
            "batch_index": 2,
            "embedding_backend": "local",
        },
        status="pending",
    )

    routed = await OutboxRouter.route_event(None, event)

    assert routed["queue"] == "embeddings_gpu"
    assert routed["task_name"] == "app.tasks.embedding_tasks.task_generate_embeddings_batch"
    assert routed["args"] == [str(gen_id), 2]


@pytest.mark.asyncio
async def test_route_embedding_batch_requested_nim():
    """Verify embedding_batch_requested with backend=nim routes to embeddings_nim_io queue."""
    gen_id = uuid4()
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=gen_id,
        event_type="embedding_batch_requested",
        payload={
            "generation_id": str(gen_id),
            "batch_index": 0,
            "embedding_backend": "nim",
        },
        status="pending",
    )

    routed = await OutboxRouter.route_event(None, event)

    assert routed["queue"] == "embeddings_nim_io"
    assert routed["task_name"] == "app.tasks.embedding_tasks.task_generate_embeddings_batch"
    assert routed["args"] == [str(gen_id), 0]


@pytest.mark.asyncio
async def test_route_embedding_batch_fallback_db_query():
    """Verify embedding_batch_requested without backend in payload queries IndexGeneration."""
    gen_id = uuid4()
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=gen_id,
        event_type="embedding_batch_requested",
        payload={
            "generation_id": str(gen_id),
            "batch_index": 1,
        },
        status="pending",
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "nim"
    mock_db.execute.return_value = mock_result

    routed = await OutboxRouter.route_event(mock_db, event)

    assert routed["queue"] == "embeddings_nim_io"
    assert routed["args"] == [str(gen_id), 1]
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_route_activation_requested():
    """Verify activation_requested routes to workflow_control queue and task_activate_generation."""
    gen_id = uuid4()
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=gen_id,
        event_type="activation_requested",
        payload={"generation_id": str(gen_id)},
        status="pending",
    )

    routed = await OutboxRouter.route_event(None, event)

    assert routed["queue"] == "workflow_control"
    assert routed["task_name"] == "app.tasks.activation_tasks.task_activate_generation"
    assert routed["args"] == [str(gen_id)]


@pytest.mark.asyncio
async def test_route_unknown_event_type_raises_unroutable():
    """Verify unknown event_type raises UnroutableEventError."""
    event = OutboxEvent(
        id=uuid4(),
        aggregate_id=uuid4(),
        event_type="unknown_custom_event",
        payload={},
        status="pending",
    )

    with pytest.raises(UnroutableEventError):
        await OutboxRouter.route_event(None, event)
