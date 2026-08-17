import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Annotated
import uuid
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_indexing_service, get_repository_service
from app.core.config import settings
from app.core.errors import AuthenticationError, RepositoryNotFoundError
from app.core.security_utils import decode_access_token
from app.db.models import IndexGeneration, OutboxEvent, Repository, User
from app.db.session import SessionLocal
from app.schemas.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexStatusResponse,
)
from app.services.git_service import GitService
from app.services.indexing_service import IndexingService
from app.services.progress_publisher import ProgressStreamPublisher, get_progress_publisher
from app.services.progress_tracker import IndexingProgressTracker
from app.services.repository_service import RepositoryService

logger = logging.getLogger(__name__)

router = APIRouter()
generation_router = APIRouter()


@router.post(
    "/{repository_id}/index",
    response_model=IndexRepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_repository(
    repository_id: UUID,
    body: IndexRepositoryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    publisher: Annotated[ProgressStreamPublisher, Depends(get_progress_publisher)],
) -> IndexRepositoryResponse:
    # 1. Lock Repository row (SELECT ... FOR UPDATE)
    stmt = (
        select(Repository)
        .where(Repository.id == repository_id, Repository.owner_id == current_user.id)
        .with_for_update()
    )
    res = await db.execute(stmt)
    repo_obj = res.scalars().first()
    if repo_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with id={repository_id} does not exist",
        )

    # 2. Capture previous desired_generation_id
    prev_desired_id = repo_obj.desired_generation_id

    # 3. Create a new IndexGeneration
    requested_ref = body.ref or repo_obj.default_branch or repo_obj.current_ref or "main"
    pipeline_version = body.pipeline_version or "v1"
    parser_version = body.parser_version or "v1"
    chunker_version = body.chunker_version or "v1"
    embedding_backend = body.embedding_backend or settings.EMBEDDING_PROVIDER
    embedding_model = body.embedding_model or settings.LOCAL_EMBEDDING_MODEL
    embedding_dimension = body.embedding_dimension or settings.EMBEDDING_DIM

    config_str = f"{embedding_backend}:{embedding_model}:{embedding_dimension}"
    config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]

    new_gen = IndexGeneration(
        id=uuid.uuid4(),
        repository_id=repo_obj.id,
        requested_ref=requested_ref,
        commit_sha=None,
        pipeline_version=pipeline_version,
        parser_version=parser_version,
        chunker_version=chunker_version,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        embedding_config_hash=config_hash,
        status="queued",
        stage_lease_owner=None,
        stage_lease_expires_at=None,
        stage_attempt=0,
    )
    db.add(new_gen)
    await db.flush()

    # 4. Set Repository.desired_generation_id = new_generation.id
    repo_obj.desired_generation_id = new_gen.id
    repo_obj.status = "indexing_queued"

    # 5. If the previous desired generation is a different non-active, non-terminal generation, mark it superseded and set terminal_at = now()
    if (
        prev_desired_id
        and prev_desired_id != repo_obj.active_generation_id
        and prev_desired_id != new_gen.id
    ):
        prev_gen_stmt = (
            select(IndexGeneration)
            .where(IndexGeneration.id == prev_desired_id)
            .with_for_update()
        )
        prev_gen_res = await db.execute(prev_gen_stmt)
        prev_gen = prev_gen_res.scalars().first()
        if prev_gen and prev_gen.status not in (
            "completed",
            "failed",
            "cancelled",
            "superseded",
        ):
            prev_gen.status = "superseded"
            prev_gen.terminal_at = datetime.now(timezone.utc)
            await publisher.publish_progress(
                generation_id=prev_gen.id,
                payload={
                    "status": "superseded",
                    "phase": "superseded",
                    "phase_name": "Indexing superseded by new request",
                },
                is_terminal=True,
            )

    # 6. Insert OutboxEvent
    outbox_event = OutboxEvent(
        id=uuid.uuid4(),
        aggregate_id=new_gen.id,
        event_type="prepare_requested",
        payload={"generation_id": str(new_gen.id)},
        status="pending",
        attempt_count=0,
        next_attempt_at=datetime.now(timezone.utc),
    )
    db.add(outbox_event)

    # 7. Commit transaction
    await db.commit()

    # Emit initial progress event
    await publisher.publish_progress(
        generation_id=new_gen.id,
        payload={
            "status": "queued",
            "phase": "queued",
            "phase_name": "Indexing request queued",
        },
    )

    # 8. Return HTTP 202 Accepted with generation_id response payload
    return IndexRepositoryResponse(
        repository_id=repo_obj.id,
        generation_id=new_gen.id,
        status="queued",
        current_ref=requested_ref,
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


@generation_router.get("/{generation_id}/stream")
@generation_router.get("/generations/{generation_id}/stream")
async def stream_generation_progress(
    generation_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[ProgressStreamPublisher, Depends(get_progress_publisher)],
    token: str | None = Query(None),
) -> StreamingResponse:
    """SSE Streaming Endpoint (Section 15).
    
    Sequence:
    1. Capture current Redis stream tail ID `C` (using XREVRANGE).
    2. Fetch PostgreSQL generation snapshot (IndexGeneration state, batch progress, error message).
    3. Yield snapshot event to client as first SSE payload.
    4. Loop streaming: XREAD BLOCK 15000 COUNT 100 STREAMS gitvane:progress:{generation_id} C.
    Sets SSE `id:` field to Redis stream ID for every streamed progress event.
    """
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
        elif "access_token" in request.cookies:
            auth_token = request.cookies.get("access_token")

    if not auth_token:
        raise AuthenticationError("Not authenticated")

    try:
        payload = decode_access_token(auth_token)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError("User not found or inactive")

    # Verify generation exists and user owns repository
    gen_stmt = (
        select(IndexGeneration, Repository)
        .join(Repository, IndexGeneration.repository_id == Repository.id)
        .where(IndexGeneration.id == generation_id, Repository.owner_id == user.id)
    )
    res = await db.execute(gen_stmt)
    row = res.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IndexGeneration with id={generation_id} not found or access denied",
        )
    gen, repo = row

    async def sse_event_generator():
        # 1. Capture current Redis stream tail ID C
        c_id = await publisher.get_tail_id(generation_id)

        # 2. Fetch PostgreSQL generation snapshot
        snap_stmt = select(IndexGeneration).where(IndexGeneration.id == generation_id)
        snap_res = await db.execute(snap_stmt)
        snap_gen = snap_res.scalar_one_or_none() or gen

        from sqlalchemy import func
        from app.db.models import EmbeddingBatch
        batch_total_stmt = select(func.count(EmbeddingBatch.id)).where(EmbeddingBatch.generation_id == generation_id)
        batch_completed_stmt = select(func.count(EmbeddingBatch.id)).where(
            EmbeddingBatch.generation_id == generation_id,
            EmbeddingBatch.status == "completed",
        )
        batch_failed_stmt = select(func.count(EmbeddingBatch.id)).where(
            EmbeddingBatch.generation_id == generation_id,
            EmbeddingBatch.status == "failed",
        )

        b_total = (await db.execute(batch_total_stmt)).scalar() or 0
        b_completed = (await db.execute(batch_completed_stmt)).scalar() or 0
        b_failed = (await db.execute(batch_failed_stmt)).scalar() or 0

        snapshot_payload = {
            "generation_id": str(snap_gen.id),
            "repository_id": str(snap_gen.repository_id),
            "status": snap_gen.status,
            "phase": snap_gen.status,
            "phase_name": f"Generation is {snap_gen.status}",
            "requested_ref": snap_gen.requested_ref,
            "commit_sha": snap_gen.commit_sha,
            "error_message": snap_gen.error_message,
            "stage_attempt": snap_gen.stage_attempt,
            "batches_total": b_total,
            "batches_completed": b_completed,
            "batches_failed": b_failed,
            "event_type": "snapshot",
        }

        # 3. Yield snapshot event as first SSE payload
        snapshot_json = json.dumps(snapshot_payload)
        yield f"id: {c_id}\nevent: progress\ndata: {snapshot_json}\n\n"

        if snap_gen.status in {"completed", "failed", "cancelled", "superseded"}:
            return

        # 4. Loop streaming: XREAD BLOCK 15000 COUNT 100 STREAMS gitvane:progress:{generation_id} C
        last_read_id = c_id
        terminal_reached = False

        while not terminal_reached:
            if await request.is_disconnected():
                logger.info("SSE client disconnected for generation stream %s", generation_id)
                break

            try:
                entries = await publisher.read_stream(
                    generation_id=generation_id,
                    last_id=last_read_id,
                    block_ms=15000,
                    count=100,
                )

                if entries:
                    for msg_id, payload in entries:
                        last_read_id = msg_id
                        payload_json = json.dumps(payload) if isinstance(payload, dict) else str(payload)
                        yield f"id: {msg_id}\nevent: progress\ndata: {payload_json}\n\n"

                        status_val = payload.get("status") if isinstance(payload, dict) else None
                        if status_val in {"completed", "failed", "cancelled", "superseded"}:
                            terminal_reached = True
                            break
                else:
                    # Timeout / ping heartbeat
                    yield ": ping\n\n"
                    # Polling fallback check in PostgreSQL using request session
                    try:
                        db_gen_stmt = select(IndexGeneration.status, IndexGeneration.error_message).where(
                            IndexGeneration.id == generation_id
                        )
                        db_res = await db.execute(db_gen_stmt)
                        db_row = db_res.fetchone()
                        if db_row and db_row.status in {"completed", "failed", "cancelled", "superseded"}:
                            term_payload = {
                                "generation_id": str(generation_id),
                                "status": db_row.status,
                                "phase": db_row.status,
                                "phase_name": f"Generation is {db_row.status}",
                                "error": db_row.error_message,
                            }
                            yield f"id: {last_read_id}\nevent: progress\ndata: {json.dumps(term_payload)}\n\n"
                            terminal_reached = True
                            break
                    except Exception as poll_exc:
                        logger.debug("SSE polling fallback check ignored exception: %s", poll_exc)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Error in SSE stream loop for generation %s: %s", generation_id, exc)
                yield ": ping\n\n"
                await asyncio.sleep(2.0)

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    if not auth_token:
        raise AuthenticationError("Not authenticated")

    try:
        payload = decode_access_token(auth_token)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError("User not found or inactive")

    try:
        repo_obj = await repo_svc.get_repository_or_raise(
            db, repository_id, owner_id=user.id
        )
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
