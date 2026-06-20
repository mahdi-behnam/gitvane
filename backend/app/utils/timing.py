import time
from contextlib import contextmanager
from typing import Generator

from app.core.logging import logger


@contextmanager
def log_duration(activity: str) -> Generator[None, None, None]:
    """Logs the elapsed time of a context block"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info(f"{activity} completed in {elapsed:.4f} seconds")
