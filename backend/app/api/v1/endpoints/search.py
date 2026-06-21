from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_semantic_search_service
from app.core.errors import EmbeddingDimensionMismatchError, RepositoryNotFoundError
from app.schemas.search import SemanticSearchRequest, SemanticSearchResponse
from app.services.semantic_search_service import SemanticSearchService

router = APIRouter()


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    body: SemanticSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[
        SemanticSearchService,
        Depends(get_semantic_search_service),
    ],
) -> SemanticSearchResponse:
    try:
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
