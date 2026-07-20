from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_indexing_service
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.db.models import Repository
from app.db.session import SessionLocal
from app.schemas.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexStatusResponse,
)
from app.services.git_service import GitService
from app.services.indexing_service import IndexingService

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
) -> IndexRepositoryResponse:
    repo_obj = await db.get(Repository, repository_id)
    if repo_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with id={repository_id} does not exist",
        )

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
) -> IndexStatusResponse:
    try:
        return await svc.get_index_status(db=db, repository_id=repository_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
