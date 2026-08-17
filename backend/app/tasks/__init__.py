"""Celery tasks module for GitVane execution engine."""

from app.tasks.activation_tasks import task_activate_generation
from app.tasks.embedding_tasks import task_generate_embeddings_batch
from app.tasks.failure_handlers import task_handle_embedding_batch_failure, task_handle_parser_failure
from app.tasks.gc_tasks import task_run_garbage_collection
from app.tasks.parser_tasks import task_prepare_and_parse

__all__ = [
    "task_prepare_and_parse",
    "task_generate_embeddings_batch",
    "task_activate_generation",
    "task_handle_parser_failure",
    "task_handle_embedding_batch_failure",
    "task_run_garbage_collection",
]
