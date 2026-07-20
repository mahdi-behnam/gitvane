import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api.deps import get_current_user, get_repository_service
from app.db.models import Repository
from app.core.errors import RepositoryNotFoundError
from app.main import app

# Configure MagicMock globally to support awaitable execute and commit
mock_result = MagicMock()
mock_result.scalar_one_or_none.return_value = 1
mock_result.scalars.return_value.first.return_value = MagicMock()
MagicMock.execute = AsyncMock(return_value=mock_result)
MagicMock.commit = AsyncMock()


@pytest.fixture(autouse=True)
def mock_dependencies(request):
    if "test_auth" in request.module.__name__:
        yield
        return

    # Mock get_current_user
    async def _mock_user():
        user = MagicMock()
        user.id = 1
        user.email = "test@example.com"
        return user
    app.dependency_overrides[get_current_user] = _mock_user

    # Mock get_repository_service (only if not test_repositories)
    if "test_repositories" not in request.module.__name__:
        mock_repo_svc = MagicMock()

        async def mock_get_repository_or_raise(db, repository_id, owner_id):
            if hasattr(db, "get") and isinstance(db.get, (AsyncMock, MagicMock)):
                try:
                    res = await db.get(Repository, repository_id)
                    if res is None:
                        raise RepositoryNotFoundError(f"Repository with id={repository_id} does not exist")
                    return res
                except RepositoryNotFoundError:
                    raise
                except Exception:
                    pass
            mock_repo = MagicMock()
            mock_repo.id = repository_id
            mock_repo.name = "test-repo"
            mock_repo.status = "ready"
            return mock_repo

        async def mock_get_repository(db, repository_id, owner_id):
            if hasattr(db, "get") and isinstance(db.get, (AsyncMock, MagicMock)):
                try:
                    res = await db.get(Repository, repository_id)
                    return res
                except Exception:
                    pass
            mock_repo = MagicMock()
            mock_repo.id = repository_id
            mock_repo.name = "test-repo"
            mock_repo.status = "ready"
            return mock_repo

        mock_repo_svc.get_repository_or_raise = AsyncMock(side_effect=mock_get_repository_or_raise)
        mock_repo_svc.get_repository = AsyncMock(side_effect=mock_get_repository)
        mock_repo_svc.list_repositories = AsyncMock(return_value=[])
        mock_repo_svc.count_repositories = AsyncMock(return_value=1)
        
        app.dependency_overrides[get_repository_service] = lambda: mock_repo_svc

    yield

    app.dependency_overrides.clear()
