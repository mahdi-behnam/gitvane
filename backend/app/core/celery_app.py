"""Celery application and queue configurations for GitVane.

Section 7: RabbitMQ / Celery Configuration
- Quorum queues declared with DLX routing to gitvane_failed_tasks
- Consumer timeouts per queue
- Late acknowledgment and worker-lost rejection enabled
- Publisher confirmations enabled
- Persistent message delivery
"""

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

# Exchanges
gitvane_exchange = Exchange("gitvane", type="direct", durable=True)
gitvane_dlx_exchange = Exchange("gitvane_dlx", type="direct", durable=True)

# Quorum Queues with Consumer Timeouts and DLX settings
task_queues = [
    Queue(
        "indexing_cpu",
        exchange=gitvane_exchange,
        routing_key="indexing_cpu",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 135 * 60 * 1000,  # 135 minutes in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "embeddings_gpu",
        exchange=gitvane_exchange,
        routing_key="embeddings_gpu",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 30 * 60 * 1000,  # 30 minutes in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "embeddings_nim_io",
        exchange=gitvane_exchange,
        routing_key="embeddings_nim_io",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 10 * 60 * 1000,  # 10 minutes in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "llm_io",
        exchange=gitvane_exchange,
        routing_key="llm_io",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 10 * 60 * 1000,  # 10 minutes in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "workflow_control",
        exchange=gitvane_exchange,
        routing_key="workflow_control",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 1 * 60 * 1000,  # 1 minute in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "evaluation_cpu",
        exchange=gitvane_exchange,
        routing_key="evaluation_cpu",
        queue_arguments={
            "x-queue-type": "quorum",
            "x-consumer-timeout": 120 * 60 * 1000,  # 120 minutes in ms
            "x-dead-letter-exchange": "gitvane_dlx",
            "x-dead-letter-routing-key": "gitvane_failed_tasks",
        },
    ),
    Queue(
        "gitvane_failed_tasks",
        exchange=gitvane_dlx_exchange,
        routing_key="gitvane_failed_tasks",
        queue_arguments={
            "x-queue-type": "quorum",
        },
    ),
]

celery_app = Celery(
    "gitvane",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    include=[
        "app.tasks.parser_tasks",
        "app.tasks.embedding_tasks",
        "app.tasks.activation_tasks",
        "app.tasks.gc_tasks",
        "app.tasks.failure_handlers",
    ],
    task_queues=task_queues,
    task_default_queue="indexing_cpu",
    task_default_exchange="gitvane",
    task_default_routing_key="indexing_cpu",
    # Celery broker options required by specification
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={"confirm_publish": True},
    task_ignore_result=True,
    task_default_delivery_mode=2,  # 2 == persistent
    # Timeouts for CPU parser task
    # Soft limit 110m (6600s) < Hard limit 120m (7200s) < stage lease 125m < RMQ timeout 135m
    task_soft_time_limit=6600,
    task_time_limit=7200,
    # Disable peer gossip, mingle, and broadcast control (avoids transient non-exclusive queues)
    worker_enable_remote_control=False,
    worker_gossip=False,
    worker_mingle=False,
)

import logging
from celery.signals import worker_process_init, worker_ready

logger = logging.getLogger(__name__)

def _warmup_local_embedding_model():
    if settings.EMBEDDING_PROVIDER.lower() == "local":
        try:
            logger.info("Celery worker: pre-warming local embedding model into singleton memory cache...")
            from app.embeddings.service import EmbeddingService

            service = EmbeddingService()
            if hasattr(service.provider, "_load_model"):
                service.provider._load_model()
            logger.info("Celery worker: local embedding model is warm and resident in memory.")
        except Exception as e:
            logger.warning("Celery worker: failed to warm up local embedding model on startup: %s", e)

@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Pre-warm embedding model inside Celery worker child processes."""
    _warmup_local_embedding_model()

@worker_ready.connect
def on_worker_ready(**kwargs):
    """Pre-warm embedding model inside solo/main worker processes."""
    _warmup_local_embedding_model()
