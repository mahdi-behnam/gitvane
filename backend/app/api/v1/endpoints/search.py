from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    get_repository_service,
    get_semantic_search_service,
)
from app.core.config import settings
from app.core.errors import EmbeddingDimensionMismatchError, RepositoryNotFoundError
from app.core.rate_limit import limiter
from app.db.models import User
from app.schemas.search import SemanticSearchRequest, SemanticSearchResponse
from app.services.repository_service import RepositoryService
from app.services.semantic_search_service import SemanticSearchService

router = APIRouter()


@router.post("/semantic", response_model=SemanticSearchResponse)
@limiter.limit(settings.RATE_LIMIT_COMPUTE)
async def semantic_search(
    request: Request,
    body: SemanticSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[
        SemanticSearchService,
        Depends(get_semantic_search_service),
    ],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SemanticSearchResponse:
    try:
        await repo_svc.get_repository_or_raise(db, body.repository_id, owner_id=current_user.id)
        return await svc.semantic_search(
            db=db,
            repository_id=body.repository_id,
            query=body.query,
            top_k=body.top_k,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EmbeddingDimensionMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
