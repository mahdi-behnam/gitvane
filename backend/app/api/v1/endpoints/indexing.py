from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_indexing_service, get_repository_service, get_current_user
from app.db.models import User
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.db.session import SessionLocal
from app.schemas.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexStatusResponse,
)
from app.services.git_service import GitService
from app.services.indexing_service import IndexingService
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post(
    "/{repository_id}/index",
    response_model=IndexRepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def index_repository(
    repository_id: int,
    body: IndexRepositoryRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IndexRepositoryResponse:
    try:
        repo_obj = await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
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
    repository_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[IndexingService, Depends(get_indexing_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IndexStatusResponse:
    try:
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        return await svc.get_index_status(db=db, repository_id=repository_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
