import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository
from app.schemas.indexing import IndexingProgressEvent

logger = logging.getLogger(__name__)


class IndexingProgressTracker:
    """In-memory progress tracker with SSE broadcast queues and DB persistence."""

    _instance: "IndexingProgressTracker | None" = None

    def __init__(self) -> None:
        self._states: Dict[UUID | Any, IndexingProgressEvent] = {}
        self._listeners: Dict[UUID | Any, Set[asyncio.Queue[IndexingProgressEvent]]] = {}
        self._start_times: Dict[UUID | Any, float] = {}

    @classmethod
    def get_instance(cls) -> "IndexingProgressTracker":
        if cls._instance is None:
            cls._instance = IndexingProgressTracker()
        return cls._instance

    def init_progress(
        self, repository_id: UUID | Any, files_total: int = 0
    ) -> IndexingProgressEvent:
        self._start_times[repository_id] = time.time()
        event = IndexingProgressEvent(
            repository_id=repository_id,
            status="indexing",
            phase="parsing",
            phase_name="Phase 1/4: Discovering & Parsing Files",
            files_total=files_total,
            files_processed=0,
            chunks_total=0,
            chunks_processed=0,
            progress_percentage=0.0,
            estimated_seconds_remaining=None,
            error=None,
        )
        self._states[repository_id] = event
        self._broadcast(repository_id, event)
        return event

    def update_progress(
        self,
        repository_id: UUID | Any,
        phase: str,
        phase_name: str,
        files_total: int | None = None,
        files_processed: int | None = None,
        chunks_total: int | None = None,
        chunks_processed: int | None = None,
        status: str = "indexing",
        error: str | None = None,
    ) -> IndexingProgressEvent:
        current = self._states.get(repository_id)
        if not current:
            current = IndexingProgressEvent(
                repository_id=repository_id,
                status=status,
                phase=phase,
                phase_name=phase_name,
            )
            self._start_times[repository_id] = time.time()

        if files_total is not None:
            current.files_total = files_total
        if files_processed is not None:
            current.files_processed = files_processed
        if chunks_total is not None:
            current.chunks_total = chunks_total
        if chunks_processed is not None:
            current.chunks_processed = chunks_processed

        current.status = status
        current.phase = phase
        current.phase_name = phase_name
        current.error = error

        # Calculate progress percentage & ETA
        current.progress_percentage = self._calc_percentage(current)
        current.estimated_seconds_remaining = self._calc_eta(repository_id, current)

        self._states[repository_id] = current
        self._broadcast(repository_id, current)
        return current

    def set_completed(
        self, repository_id: UUID | Any, files_indexed: int, chunks_indexed: int
    ) -> IndexingProgressEvent:
        event = IndexingProgressEvent(
            repository_id=repository_id,
            status="indexed",
            phase="completed",
            phase_name="Indexing Complete",
            files_total=files_indexed,
            files_processed=files_indexed,
            chunks_total=chunks_indexed,
            chunks_processed=chunks_indexed,
            progress_percentage=100.0,
            estimated_seconds_remaining=0,
        )
        self._states[repository_id] = event
        self._broadcast(repository_id, event)
        self._start_times.pop(repository_id, None)
        return event

    def set_failed(self, repository_id: UUID | Any, error_message: str) -> IndexingProgressEvent:
        current = self._states.get(repository_id)
        event = IndexingProgressEvent(
            repository_id=repository_id,
            status="index_failed",
            phase="failed",
            phase_name="Indexing Failed",
            files_total=current.files_total if current else 0,
            files_processed=current.files_processed if current else 0,
            chunks_total=current.chunks_total if current else 0,
            chunks_processed=current.chunks_processed if current else 0,
            progress_percentage=current.progress_percentage if current else 0.0,
            estimated_seconds_remaining=None,
            error=error_message,
        )
        self._states[repository_id] = event
        self._broadcast(repository_id, event)
        self._start_times.pop(repository_id, None)
        return event

    def get_progress(self, repository_id: UUID | Any) -> IndexingProgressEvent | None:
        return self._states.get(repository_id)

    def load_from_metadata(
        self, repository_id: UUID | Any, metadata: dict | None, status: str
    ) -> IndexingProgressEvent | None:
        if status == "indexed":
            return IndexingProgressEvent(
                repository_id=repository_id,
                status="indexed",
                phase="completed",
                phase_name="Indexing Complete",
                progress_percentage=100.0,
                estimated_seconds_remaining=0,
            )

        if metadata and "indexing_progress" in metadata:
            try:
                progress_dict = metadata["indexing_progress"]
                event = IndexingProgressEvent(**progress_dict)
                if status == "indexing" and event.status == "indexed":
                    event.status = "indexing"
                    event.phase = "parsing"
                    event.phase_name = "Phase 1/4: Discovering & Parsing Files"
                    event.progress_percentage = 0.0
                    event.estimated_seconds_remaining = None
                self._states[repository_id] = event
                return event
            except Exception as e:
                logger.warning(
                    f"Failed to parse indexing_progress metadata for repo {repository_id}: {e}"
                )

        if status == "indexing":
            return IndexingProgressEvent(
                repository_id=repository_id,
                status="indexing",
                phase="parsing",
                phase_name="Phase 1/4: Discovering & Parsing Files",
                progress_percentage=0.0,
                estimated_seconds_remaining=None,
            )

        return None

    async def sync_to_db(self, db: AsyncSession, repository_id: UUID | Any) -> None:
        event = self._states.get(repository_id)
        if not event:
            return

        try:
            repo_obj = await db.get(Repository, repository_id)
            if repo_obj:
                metadata = repo_obj.repo_metadata or {}
                metadata["indexing_progress"] = event.model_dump(mode="json")
                repo_obj.repo_metadata = metadata
                await db.commit()
        except Exception as exc:
            logger.error(
                f"Failed to sync indexing progress to DB for repo {repository_id}: {exc}"
            )

    async def subscribe(
        self, repository_id: UUID | Any
    ) -> AsyncGenerator[IndexingProgressEvent, None]:
        queue: asyncio.Queue[IndexingProgressEvent] = asyncio.Queue()
        if repository_id not in self._listeners:
            self._listeners[repository_id] = set()
        self._listeners[repository_id].add(queue)

        # Send immediate initial snapshot if state exists
        if repository_id in self._states:
            await queue.put(self._states[repository_id])

        try:
            while True:
                event = await queue.get()
                yield event
                if event.status in {"indexed", "index_failed"}:
                    break
        finally:
            if repository_id in self._listeners:
                self._listeners[repository_id].discard(queue)
                if not self._listeners[repository_id]:
                    self._listeners.pop(repository_id, None)

    def _broadcast(self, repository_id: UUID | Any, event: IndexingProgressEvent) -> None:
        if repository_id in self._listeners:
            for queue in list(self._listeners[repository_id]):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    def _calc_percentage(self, event: IndexingProgressEvent) -> float:
        if event.status == "indexed":
            return 100.0
        if event.status == "index_failed":
            return event.progress_percentage

        # Phase weights
        # parsing: 0% -> 25%
        # saving: 25% -> 30%
        # embeddings: 30% -> 85%
        # graph_and_commits: 85% -> 99%
        pct = 0.0

        if event.phase == "parsing":
            ratio = (
                (event.files_processed / event.files_total)
                if event.files_total > 0
                else 0.0
            )
            pct = 0.0 + (ratio * 25.0)

        elif event.phase == "saving":
            pct = 25.0 + 5.0

        elif event.phase == "embeddings":
            ratio = (
                (event.chunks_processed / event.chunks_total)
                if event.chunks_total > 0
                else 0.0
            )
            pct = 30.0 + (ratio * 55.0)

        elif event.phase == "graph_and_commits":
            pct = 85.0 + 10.0

        return round(min(pct, 99.0), 1)

    def _calc_eta(
        self, repository_id: UUID | Any, event: IndexingProgressEvent
    ) -> int | None:
        if event.status in {"indexed", "index_failed"} or event.phase == "completed":
            return 0

        start_time = self._start_times.get(repository_id)
        if not start_time:
            return None

        elapsed = time.time() - start_time
        if elapsed < 2.0:
            return None  # Wait a couple seconds for throughput rate to stabilize

        pct = event.progress_percentage
        if pct <= 1.0:
            return None

        total_est_seconds = (elapsed / pct) * 100.0
        remaining = int(total_est_seconds - elapsed)
        return max(remaining, 1)
