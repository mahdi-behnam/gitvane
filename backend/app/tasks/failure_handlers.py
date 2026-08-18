"""Celery tasks for terminal failure handling (workflow_control queue)."""

import asyncio
import logging
from uuid import UUID

from celery import Task

from app.core.async_runner import run_sync_in_worker_loop
from app.core.celery_app import celery_app
from app.db.session import WorkerSessionLocal as SessionLocal
from app.execution.failure_engine import (
    handle_embedding_batch_failure,
    handle_parser_failure,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.failure_handlers.task_handle_parser_failure",
    queue="workflow_control",
    acks_late=True,
    reject_on_worker_lost=True,
)
def task_handle_parser_failure(
    self: Task,
    generation_id_str: str,
    task_id: str,
    stage_attempt: int,
    error_message: str,
) -> dict:
    """Fenced terminal parser failure task."""
    generation_id = UUID(generation_id_str)
    return run_sync_in_worker_loop(_async_parser_failure(generation_id, task_id, stage_attempt, error_message))


async def _async_parser_failure(
    generation_id: UUID,
    task_id: str,
    stage_attempt: int,
    error_message: str,
) -> dict:
    async with SessionLocal() as db:
        status = await handle_parser_failure(
            db=db,
            generation_id=generation_id,
            task_id=task_id,
            stage_attempt=stage_attempt,
            error_message=error_message,
        )
        await db.commit()
        return {"status": status}


@celery_app.task(
    bind=True,
    name="app.tasks.failure_handlers.task_handle_embedding_batch_failure",
    queue="workflow_control",
    acks_late=True,
    reject_on_worker_lost=True,
)
def task_handle_embedding_batch_failure(
    self: Task,
    generation_id_str: str,
    batch_index: int,
    task_id: str,
    error_message: str,
) -> dict:
    """Fenced terminal embedding batch failure task."""
    generation_id = UUID(generation_id_str)
    return run_sync_in_worker_loop(_async_embedding_batch_failure(generation_id, batch_index, task_id, error_message))


async def _async_embedding_batch_failure(
    generation_id: UUID,
    batch_index: int,
    task_id: str,
    error_message: str,
) -> dict:
    async with SessionLocal() as db:
        status = await handle_embedding_batch_failure(
            db=db,
            generation_id=generation_id,
            batch_index=batch_index,
            task_id=task_id,
            error_message=error_message,
        )
        await db.commit()
        return {"status": status}
