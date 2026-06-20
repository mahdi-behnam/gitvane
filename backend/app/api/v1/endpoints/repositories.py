from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_repository_service
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.schemas.repository import RepositoryCreate, RepositoryList, RepositoryOut
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def create_repository(
    body: RepositoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RepositoryOut:
    """
    Register and clone (or adopt) a Git repository.

    - If `clone_url` is provided, the repository is cloned into the workspace.
    - If `local_path` is provided instead, the path is validated and adopted.
    - Set `index_now=true` to queue indexing immediately after registration
      (indexing pipeline must be active; see Phase 4).
    - Returns the created repository record.
    """
    try:
        repo = await svc.create_repository(
            db=db,
            name=body.name,
            clone_url=body.clone_url or "",
            branch=body.branch,
            local_path=body.local_path,
            index_now=body.index_now,
        )
        return RepositoryOut.model_validate(repo)
    except InvalidPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except GitOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("", response_model=RepositoryList)
async def list_repositories(
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
) -> RepositoryList:
    """Return a paginated list of registered repositories."""
    repos = await svc.list_repositories(db=db, skip=skip, limit=limit)
    total = await svc.count_repositories(db=db)
    return RepositoryList(
        items=[RepositoryOut.model_validate(r) for r in repos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{repository_id}", response_model=RepositoryOut)
async def get_repository(
    repository_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
) -> RepositoryOut:
    """Fetch a single repository by its ID."""
    try:
        repo = await svc.get_repository_or_raise(db=db, repository_id=repository_id)
        return RepositoryOut.model_validate(repo)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
) -> None:
    """
    Delete a repository record and remove its local clone from disk.

    Returns 204 No Content on success, 404 if the repository does not exist.
    """
    try:
        await svc.delete_repository_or_raise(db=db, repository_id=repository_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
