from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_db,
    get_repository_service,
    get_semantic_search_service,
    get_test_recommendation_service,
)
from app.core.config import settings
from app.core.errors import RepositoryNotFoundError
from app.core.rate_limit import limiter
from app.db.models import User
from app.schemas.tests import TestRecommendationRequest, TestRecommendationResponse
from app.services.repository_service import RepositoryService
from app.services.semantic_search_service import SemanticSearchService
from app.services.test_recommendation_service import TestRecommendationService

router = APIRouter()


@router.post("/recommend", response_model=TestRecommendationResponse)
@limiter.limit(settings.RATE_LIMIT_COMPUTE)
async def recommend_tests(
    request: Request,
    body: TestRecommendationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[
        TestRecommendationService,
        Depends(get_test_recommendation_service),
    ],
    semantic_svc: Annotated[
        SemanticSearchService,
        Depends(get_semantic_search_service),
    ],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TestRecommendationResponse:
    try:
        await repo_svc.get_repository_or_raise(db, body.repository_id, owner_id=current_user.id)
        return await svc.recommend_for_repository(
            db=db,
            repository_id=body.repository_id,
            changed_files=body.changed_files,
            impacted_files=body.impacted_files,
            top_k=body.top_k,
            semantic_search_service=semantic_svc,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
