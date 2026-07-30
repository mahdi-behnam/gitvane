import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_indexing_service, get_repository_service
from app.core.errors import AuthenticationError, RepositoryNotFoundError
from app.core.security_utils import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexStatusResponse,
)
from app.services.git_service import GitService
from app.services.indexing_service import IndexingService
from app.services.progress_tracker import IndexingProgressTracker
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post(
    "/{repository_id}/index",
    response_model=IndexRepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_repository(
    repository_id: UUID,
    body: IndexRepositoryRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IndexRepositoryResponse:
    try:
        repo_obj = await repo_svc.get_repository_or_raise(
            db, repository_id, owner_id=current_user.id
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    repo_obj.status = "indexing"
    await db.commit()

    async def async_indexing_task() -> None:
        async with SessionLocal() as async_db:
            try:
                git_service = GitService()
                indexing_service = IndexingService(git_service=git_service)
                await indexing_service.index_repository(
                    db=async_db,
                    repository_id=repository_id,
                    ref=body.ref,
                )
            except Exception:
                pass

    background_tasks.add_task(async_indexing_task)

    return IndexRepositoryResponse(
        repository_id=repository_id,
        status="indexing",
        files_indexed=0,
        files_skipped=0,
        symbols_indexed=0,
        chunks_indexed=0,
        embeddings_indexed=0,
        dependency_edges_indexed=0,
        commits_indexed=0,
    )


@router.get("/{repository_id}/index/status", response_model=IndexStatusResponse)
async def get_index_status(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[IndexingService, Depends(get_indexing_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IndexStatusResponse:
    try:
        await repo_svc.get_repository_or_raise(
            db, repository_id, owner_id=current_user.id
        )
        return await svc.get_index_status(db=db, repository_id=repository_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{repository_id}/index/events")
async def index_events(
    repository_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    token: str | None = Query(None),
) -> StreamingResponse:
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
        elif "access_token" in request.cookies:
            auth_token = request.cookies.get("access_token")

    user_id: int | None = None
    if auth_token:
        try:
            payload = decode_access_token(auth_token)
            user_id = int(payload["sub"])
        except Exception:
            pass

    try:
        if user_id is not None:
            repo_obj = await repo_svc.get_repository_or_raise(
                db, repository_id, owner_id=user_id
            )
        else:
            repo_obj = await repo_svc.get_repository_or_raise(db, repository_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    tracker = IndexingProgressTracker.get_instance()

    async def event_generator():
        # Load or snapshot current state
        initial_event = tracker.get_progress(repository_id)
        if not initial_event:
            initial_event = tracker.load_from_metadata(
                repository_id, repo_obj.repo_metadata, repo_obj.status
            )

        if initial_event:
            data = initial_event.model_dump_json()
            yield f"event: progress\ndata: {data}\n\n"

        if repo_obj.status not in {"indexing"}:
            return

        loop = asyncio.get_running_loop()
        subscriber_gen = tracker.subscribe(repository_id)

        try:
            while True:
                # Wait for next event or heartbeat timeout
                try:
                    event = await asyncio.wait_for(subscriber_gen.__anext__(), timeout=15.0)
                    data = event.model_dump_json()
                    yield f"event: progress\ndata: {data}\n\n"
                    if event.status in {"indexed", "index_failed"}:
                        await asyncio.sleep(0.5)
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
                except StopAsyncIteration:
                    break
        finally:
            await subscriber_gen.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

