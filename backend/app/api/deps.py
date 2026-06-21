from app.db.session import get_db
from app.services.git_service import GitService
from app.services.impact_service import ImpactService
from app.services.indexing_service import IndexingService
from app.services.repository_service import RepositoryService
from app.services.risk_service import RiskService
from app.services.semantic_search_service import SemanticSearchService
from app.services.test_recommendation_service import TestRecommendationService


def get_git_service() -> GitService:
    """Returns a GitService instance"""
    return GitService()


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


def get_test_recommendation_service() -> TestRecommendationService:
    """Returns a TestRecommendationService instance."""
    return TestRecommendationService()


__all__ = [
    "get_db",
    "get_git_service",
    "get_impact_service",
    "get_indexing_service",
    "get_repository_service",
    "get_risk_service",
    "get_semantic_search_service",
    "get_test_recommendation_service",
]
