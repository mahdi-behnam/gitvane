from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_graph_service, get_repository_service, get_current_user
from app.db.models import User
from app.core.errors import RepositoryNotFoundError
from app.schemas.graph import GraphResponse
from app.services.graph_service import GraphService
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.get(
    "/repositories/{repository_id}/file/{file_id}/neighbors",
    response_model=GraphResponse,
)
async def get_file_neighbors(
    repository_id: int,
    file_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[GraphService, Depends(get_graph_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GraphResponse:
    try:
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        return await svc.get_file_neighbors(
            db=db,
            repository_id=repository_id,
            file_id=file_id,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/repositories/{repository_id}/subgraph",
    response_model=GraphResponse,
)
async def get_repository_subgraph(
    repository_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[GraphService, Depends(get_graph_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    max_nodes: int = Query(500, ge=1, le=2000),
    language: str | None = Query(None),
    include_tests: bool = Query(True),
) -> GraphResponse:
    try:
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        return await svc.get_repository_subgraph(
            db=db,
            repository_id=repository_id,
            max_nodes=max_nodes,
            language=language,
            include_tests=include_tests,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
