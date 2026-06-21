from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_indexing_service
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.schemas.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexStatusResponse,
)
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.post("/{repository_id}/index", response_model=IndexRepositoryResponse)
async def index_repository(
    repository_id: int,
    body: IndexRepositoryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexRepositoryResponse:
    try:
        return await svc.index_repository(
            db=db,
            repository_id=repository_id,
            ref=body.ref,
            max_commits=body.max_commits,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvalidPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except GitOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


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
