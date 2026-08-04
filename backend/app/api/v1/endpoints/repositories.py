from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_repository_service, get_current_user
from app.db.models import User
from app.core.errors import GitOperationError, InvalidPathError, RepositoryNotFoundError
from app.schemas.repository import (
    FileSearchResult,
    RefSearchResult,
    RepositoryCreate,
    RepositoryList,
    RepositoryOut,
)
from app.services.repository_service import RepositoryService


router = APIRouter()


@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def create_repository(
    body: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
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
            owner_id=current_user.id,
            name=body.name,
            clone_url=body.clone_url or "",
            branch=body.branch,
            local_path=None,
            index_now=body.index_now,
            pat=body.pat,
        )

        if body.index_now:
            repo.status = "indexing"
            await db.commit()
            await db.refresh(repo)

            async def run_indexing_task():
                from app.db.session import SessionLocal
                from app.api.deps import get_indexing_service
                async with SessionLocal() as async_db:
                    try:
                        indexing_svc = get_indexing_service()
                        await indexing_svc.index_repository(
                            db=async_db,
                            repository_id=repo.id,
                            ref=body.branch,  # Index the specified branch
                        )
                    except Exception:
                        pass

            background_tasks.add_task(run_indexing_task)

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
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
) -> RepositoryList:
    """Return a paginated list of registered repositories."""
    repos = await svc.list_repositories(db=db, owner_id=current_user.id, skip=skip, limit=limit)
    total = await svc.count_repositories(db=db, owner_id=current_user.id)
    return RepositoryList(
        items=[RepositoryOut.model_validate(r) for r in repos],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{repository_id}", response_model=RepositoryOut)
async def get_repository(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RepositoryOut:
    """Fetch a single repository by its ID."""
    try:
        repo = await svc.get_repository_or_raise(db=db, repository_id=repository_id, owner_id=current_user.id)
        return RepositoryOut.model_validate(repo)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a repository record and remove its local clone from disk.

    Returns 204 No Content on success, 404 if the repository does not exist.
    """
    try:
        await svc.delete_repository_or_raise(db=db, repository_id=repository_id, owner_id=current_user.id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{repository_id}/languages", response_model=list[str])
async def list_repository_languages(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[str]:
    """Return distinct indexed programming languages for a repository."""
    try:
        await svc.get_repository_or_raise(db=db, repository_id=repository_id, owner_id=current_user.id)
        from sqlalchemy import select
        from app.db.models import CodeFile

        stmt = (
            select(CodeFile.language)
            .where(CodeFile.repository_id == repository_id, CodeFile.language != "")
            .distinct()
            .order_by(CodeFile.language)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{repository_id}/files/search", response_model=list[FileSearchResult])
async def search_repository_files(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: str = Query("", description="Sub-path query to filter files"),
    limit: int = Query(50, ge=1, le=200, description="Max matching files to return"),
) -> list[FileSearchResult]:
    """Perform fast autocomplete file search in an indexed repository."""
    try:
        await svc.get_repository_or_raise(db=db, repository_id=repository_id, owner_id=current_user.id)
        from sqlalchemy import select
        from app.db.models import CodeFile

        stmt = select(CodeFile).where(CodeFile.repository_id == repository_id)
        if query.trim() if hasattr(query, "trim") else query.strip():
            search_pattern = f"%{query.strip()}%"
            stmt = stmt.where(CodeFile.path.ilike(search_pattern))
        stmt = stmt.order_by(CodeFile.path).limit(limit)

        res = await db.execute(stmt)
        files = res.scalars().all()

        return [
            FileSearchResult(
                id=f.id,
                path=f.path,
                language=f.language,
                loc=f.loc,
                is_test=f.is_test,
            )
            for f in files
        ]
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/{repository_id}/refs", response_model=list[RefSearchResult])
async def list_repository_refs(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: str = Query("", description="Optional search query to filter branches/tags/commits"),
    limit: int = Query(50, ge=1, le=200, description="Max refs to return"),
    ref_type: str | None = Query(None, description="Filter by ref type ('branch', 'tag', or 'commit')"),
) -> list[RefSearchResult]:
    """Perform fast autocomplete git ref search (branches, tags, commits) in a repository."""
    try:
        raw_refs = await svc.list_repository_refs(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
            query=query,
            limit=limit,
            ref_type=ref_type,
        )
        return [RefSearchResult.model_validate(r) for r in raw_refs]
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except GitOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


