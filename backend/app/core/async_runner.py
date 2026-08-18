"""Persistent worker event loop for Celery tasks.

Maintains a single long-lived asyncio event loop running in a background thread
so that SQLAlchemy AsyncEngine connection pools (asyncpg) and Redis clients
stay alive across multiple Celery task executions without TCP connection churn.
"""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_thread: threading.Thread | None = None
_lock = threading.Lock()


def get_worker_event_loop() -> asyncio.AbstractEventLoop:
    """Return a process-wide, long-lived asyncio event loop running in a dedicated thread."""
    global _worker_loop, _worker_loop_thread
    if _worker_loop is not None and _worker_loop.is_running():
        return _worker_loop

    with _lock:
        if _worker_loop is not None and _worker_loop.is_running():
            return _worker_loop

        loop = asyncio.new_event_loop()

        def _run_loop(target_loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(target_loop)
            target_loop.run_forever()

        thread = threading.Thread(
            target=_run_loop,
            args=(loop,),
            daemon=True,
            name="CeleryWorkerAsyncLoop",
        )
        thread.start()
        _worker_loop = loop
        _worker_loop_thread = thread
        return _worker_loop


def run_sync_in_worker_loop(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine on the long-lived worker event loop synchronously."""
    loop = get_worker_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()
