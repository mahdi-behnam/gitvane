from app.db.session import get_db
from app.services.git_service import GitService
from app.services.impact_service import ImpactService
from app.services.indexing_service import IndexingService
from app.services.repository_service import RepositoryService
from app.services.semantic_search_service import SemanticSearchService


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


__all__ = [
    "get_db",
    "get_git_service",
    "get_impact_service",
    "get_indexing_service",
    "get_repository_service",
    "get_semantic_search_service",
]
