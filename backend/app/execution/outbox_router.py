"""Outbox Event Router for GitVane execution pipeline.

Maps OutboxEvent instances to Celery queue names and task signatures based on
durable generation configuration.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IndexGeneration, OutboxEvent

logger = logging.getLogger(__name__)


class UnroutableEventError(Exception):
    """Raised when an outbox event cannot be routed to a Celery task."""
    pass


class OutboxRouter:
    """Outbox event router mapping event_type to Celery task execution parameters."""

    @staticmethod
    async def route_event(
        db: Optional[AsyncSession],
        event: OutboxEvent,
    ) -> dict[str, Any]:
        """Route an outbox event to queue name, task name, args, and kwargs.
        
        Args:
            db: Optional AsyncSession for resolving missing configuration from PostgreSQL.
            event: The OutboxEvent record to route.

        Returns:
            dict containing:
                - queue: str (target Celery queue)
                - task_name: str (fully qualified Celery task name)
                - args: list[Any] (positional task arguments)
                - kwargs: dict[str, Any] (keyword task arguments)
        """
        event_type = event.event_type
        payload = event.payload or {}
        generation_id_str = str(payload.get("generation_id") or event.aggregate_id)

        if event_type == "prepare_requested":
            return {
                "queue": "indexing_cpu",
                "task_name": "app.tasks.parser_tasks.task_prepare_and_parse",
                "args": [generation_id_str],
                "kwargs": {},
            }

        elif event_type == "embedding_batch_requested":
            if "batch_index" not in payload:
                raise UnroutableEventError(
                    f"embedding_batch_requested event {event.id} missing 'batch_index' in payload"
                )

            batch_index = int(payload["batch_index"])
            backend = payload.get("embedding_backend") or payload.get("backend")

            # Derive backend from durable IndexGeneration configuration if not in payload
            if not backend and db is not None:
                stmt = select(IndexGeneration.embedding_backend).where(
                    IndexGeneration.id == UUID(generation_id_str)
                )
                res = await db.execute(stmt)
                backend = res.scalar_one_or_none()

            if backend == "nim":
                queue = "embeddings_nim_io"
            elif backend == "local" or backend is None or backend == "":
                queue = "embeddings_gpu"
            else:
                # Default to embeddings_gpu for local backends, log warning for unexpected string
                logger.warning(
                    "Unknown embedding backend '%s' for event %s; defaulting to embeddings_gpu",
                    backend,
                    event.id,
                )
                queue = "embeddings_gpu"

            return {
                "queue": queue,
                "task_name": "app.tasks.embedding_tasks.task_generate_embeddings_batch",
                "args": [generation_id_str, batch_index],
                "kwargs": {},
            }

        elif event_type == "activation_requested":
            return {
                "queue": "workflow_control",
                "task_name": "app.tasks.activation_tasks.task_activate_generation",
                "args": [generation_id_str],
                "kwargs": {},
            }

        else:
            raise UnroutableEventError(
                f"Unknown or unroutable event_type '{event_type}' for event {event.id}"
            )
