from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.errors import AuthenticationError
from app.core.security_utils import decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.services.evaluation_service import EvaluationService
from app.services.git_service import GitService
from app.services.graph_service import GraphService
from app.services.impact_service import ImpactService
from app.services.indexing_service import IndexingService
from app.services.repository_service import RepositoryService
from app.services.risk_service import RiskService
from app.services.semantic_search_service import SemanticSearchService
from app.services.test_recommendation_service import TestRecommendationService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Invalid or expired credentials")
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid or expired credentials")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError("User not found")
    return user



def get_git_service() -> GitService:
    """Returns a GitService instance"""
    return GitService()


def get_graph_service() -> GraphService:
    """Returns a GraphService instance."""
    return GraphService()


def get_repository_service() -> RepositoryService:
    """Returns a RepositoryService instance injected with GitService"""
    return RepositoryService(get_git_service())


def get_indexing_service() -> IndexingService:
    """Returns an IndexingService instance injected with GitService."""
    return IndexingService(get_git_service())


def get_impact_service() -> ImpactService:
    """Returns an ImpactService instance injected with GitService."""
    return ImpactService(get_git_service())


def get_semantic_search_service() -> SemanticSearchService:
    """Returns a SemanticSearchService instance."""
    return SemanticSearchService()


def get_risk_service() -> RiskService:
    """Returns a RiskService instance."""
    return RiskService()


def get_evaluation_service() -> EvaluationService:
    """Returns an EvaluationService instance."""
    return EvaluationService(get_semantic_search_service())


def get_test_recommendation_service() -> TestRecommendationService:
    """Returns a TestRecommendationService instance."""
    return TestRecommendationService()


__all__ = [
    "get_db",
    "get_current_user",
    "get_evaluation_service",
    "get_git_service",
    "get_graph_service",
    "get_impact_service",
    "get_indexing_service",
    "get_repository_service",
    "get_risk_service",
    "get_semantic_search_service",
    "get_test_recommendation_service",
]
