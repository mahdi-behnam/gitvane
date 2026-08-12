"""Celery task for generation activation (workflow_control queue)."""

import asyncio
import logging
from uuid import UUID

from celery import Task

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.execution.activation_engine import activate_generation

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.activation_tasks.task_activate_generation",
    queue="workflow_control",
    acks_late=True,
    reject_on_worker_lost=True,
)
def task_activate_generation(self: Task, generation_id_str: str) -> dict:
    """Task to activate an IndexGeneration on the workflow_control queue."""
    generation_id = UUID(generation_id_str)
    return asyncio.run(_async_activate_generation(generation_id))


async def _async_activate_generation(generation_id: UUID) -> dict:
    async with SessionLocal() as db:
        try:
            result = await activate_generation(db, generation_id)
            await db.commit()
            return result
        except Exception as exc:
            logger.exception("Error activating generation %s: %s", generation_id, exc)
            await db.rollback()
            raise exc
