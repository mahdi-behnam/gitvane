from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_semantic_search_service,
    get_test_recommendation_service,
    get_repository_service,
    get_current_user,
)
from app.db.models import User
from app.core.errors import RepositoryNotFoundError
from app.schemas.tests import TestRecommendationRequest, TestRecommendationResponse
from app.services.semantic_search_service import SemanticSearchService
from app.services.test_recommendation_service import TestRecommendationService
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post("/recommend", response_model=TestRecommendationResponse)
async def recommend_tests(
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
