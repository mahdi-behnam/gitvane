from app.db.session import get_db
from app.services.git_service import GitService
from app.services.indexing_service import IndexingService
from app.services.repository_service import RepositoryService


def get_git_service() -> GitService:
    """Returns a GitService instance"""
    return GitService()


def get_repository_service() -> RepositoryService:
    """Returns a RepositoryService instance injected with GitService"""
    return RepositoryService(get_git_service())


def get_indexing_service() -> IndexingService:
    """Returns an IndexingService instance injected with GitService."""
    return IndexingService(get_git_service())


__all__ = [
    "get_db",
    "get_git_service",
    "get_indexing_service",
    "get_repository_service",
]
