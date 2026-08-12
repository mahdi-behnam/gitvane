"""Celery task for periodic garbage collection (workflow_control queue)."""

import asyncio
import logging
from typing import Any, Dict

from celery import Task

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.garbage_collection_service import GarbageCollectionService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.gc_tasks.task_run_garbage_collection",
    queue="workflow_control",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=300,
    time_limit=360,
)
def task_run_garbage_collection(
    self: Task,
    retention_hours: int = 24,
    generation_limit: int = 100,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    """Celery task to trigger periodic garbage collection for stale index generations."""
    logger.info(
        "Starting garbage collection task (retention_hours=%d, generation_limit=%d, batch_size=%d)",
        retention_hours,
        generation_limit,
        batch_size,
    )
    return asyncio.run(
        _async_run_garbage_collection(
            retention_hours=retention_hours,
            generation_limit=generation_limit,
            batch_size=batch_size,
        )
    )


async def _async_run_garbage_collection(
    retention_hours: int,
    generation_limit: int,
    batch_size: int,
) -> Dict[str, Any]:
    gc_service = GarbageCollectionService()
    async with SessionLocal() as db:
        return await gc_service.run_garbage_collection(
            db=db,
            retention_hours=retention_hours,
            generation_limit=generation_limit,
            batch_size=batch_size,
        )
