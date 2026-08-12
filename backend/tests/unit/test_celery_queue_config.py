"""Unit tests for Celery queue and broker configuration (Section 7)."""

import pytest

from app.core.celery_app import celery_app, gitvane_dlx_exchange, gitvane_exchange


def test_celery_quorum_queues_and_timeouts():
    """Verify Celery app has all 7 quorum queues declared with exact consumer timeouts."""
    queues = {q.name: q for q in celery_app.conf.task_queues}

    required_queues = {
        "indexing_cpu": 135 * 60 * 1000,     # 135m
        "embeddings_gpu": 30 * 60 * 1000,     # 30m
        "embeddings_nim_io": 10 * 60 * 1000,  # 10m
        "llm_io": 10 * 60 * 1000,             # 10m
        "workflow_control": 1 * 60 * 1000,    # 1m
        "evaluation_cpu": 120 * 60 * 1000,    # 120m
        "gitvane_failed_tasks": None,         # DLX
    }

    assert set(required_queues.keys()).issubset(set(queues.keys()))

    for qname, expected_timeout in required_queues.items():
        queue = queues[qname]
        args = queue.queue_arguments
        assert args.get("x-queue-type") == "quorum", f"Queue {qname} must be a quorum queue"

        if expected_timeout is not None:
            assert args.get("x-consumer-timeout") == expected_timeout, (
                f"Queue {qname} timeout expected {expected_timeout}, got {args.get('x-consumer-timeout')}"
            )
            assert args.get("x-dead-letter-exchange") == "gitvane_dlx", (
                f"Queue {qname} DLX exchange must be gitvane_dlx"
            )
            assert args.get("x-dead-letter-routing-key") == "gitvane_failed_tasks", (
                f"Queue {qname} DLX routing key must be gitvane_failed_tasks"
            )


def test_celery_broker_options_and_time_limits():
    """Verify Celery broker options: late acks, worker lost rejection, publisher confirms, limits."""
    conf = celery_app.conf

    assert conf.task_acks_late is True, "task_acks_late must be True"
    assert conf.task_reject_on_worker_lost is True, "task_reject_on_worker_lost must be True"
    assert conf.broker_transport_options.get("confirm_publish") is True, "confirm_publish must be True"
    assert conf.task_ignore_result is True, "task_ignore_result must be True by default"
    assert conf.task_default_delivery_mode == 2, "task_default_delivery_mode must be 2 (persistent)"

    # Time limits hierarchy: Soft limit 110m (6600s) < Hard limit 120m (7200s)
    assert conf.task_soft_time_limit == 6600, "soft time limit must be 6600s (110m)"
    assert conf.task_time_limit == 7200, "hard time limit must be 7200s (120m)"
