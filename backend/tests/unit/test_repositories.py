"""Unit tests for the /api/v1/repositories endpoints.

Uses FastAPI dependency overrides to mock the DB session and
RepositoryService, so no live database is required.
"""

from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_repository_service
from app.core.errors import GitOperationError, RepositoryNotFoundError, PrivateRepositoryNotSupportedError
from app.db.models import Repository
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_repository_service
from app.core.errors import GitOperationError, RepositoryNotFoundError, PrivateRepositoryNotSupportedError
from app.db.models import Repository
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc
TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


def _make_repo(
    repo_id: UUID | Any = TEST_UUID,
    name: str = "test-repo",
    clone_url: str = "https://github.com/example/test-repo.git",
    status: str = "ready",
    active_generation_id: UUID | None = UUID("22222222-2222-2222-2222-222222222222"),
) -> Repository:
    """Build a minimal Repository ORM stub for use in tests."""
    repo = MagicMock(spec=Repository)
    repo.id = repo_id
    repo.name = name
    repo.clone_url = clone_url
    repo.local_path = f"/workspace/repos/repo_{repo_id}"
    repo.default_branch = "main"
    repo.current_ref = "abc123def456"
    repo.status = status
    repo.active_generation_id = active_generation_id
    repo.desired_generation_id = None
    repo.last_indexed_commit = None
    repo.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    repo.updated_at = datetime(2024, 1, 1, tzinfo=UTC)
    repo.indexed_at = None
    repo.repo_metadata = None
    return repo


async def _noop_db() -> AsyncGenerator[Any, None]:
    """No-op DB dependency override — service is fully mocked anyway."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    yield db


# ---------------------------------------------------------------------------
# Tests — POST /api/v1/repositories
# ---------------------------------------------------------------------------


def test_create_repository_success() -> None:
    """POST returns 201 and the new repository payload on success (default index_now=True)."""
    repo = _make_repo(status="indexing_queued")
    mock_svc = MagicMock()
    mock_svc.create_repository = AsyncMock(return_value=repo)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={
                "name": "test-repo",
                "clone_url": "https://github.com/example/test-repo.git",
                "branch": "main",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(TEST_UUID)
        assert data["name"] == "test-repo"
        assert data["status"] == "indexing_queued"
    finally:
        app.dependency_overrides.clear()


def test_create_repository_with_index_now_false() -> None:
    """POST with index_now=False sets status to ready without kicking off indexing."""
    repo = _make_repo(status="ready")

    mock_svc = MagicMock()
    mock_svc.create_repository = AsyncMock(return_value=repo)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={
                "name": "test-repo",
                "clone_url": "https://github.com/example/test-repo.git",
                "branch": "main",
                "index_now": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ready"
    finally:
        app.dependency_overrides.clear()


def test_create_repository_missing_url_and_path() -> None:
    """POST returns 422 when neither clone_url nor local_path is provided."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "branch": "main"},
    )
    assert response.status_code == 422


def test_create_repository_missing_branch() -> None:
    """POST returns 422 when branch is not provided or empty."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "clone_url": "https://github.com/example/test-repo.git"},
    )
    assert response.status_code == 422

    response_empty = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "clone_url": "https://github.com/example/test-repo.git", "branch": "  "},
    )
    assert response_empty.status_code == 422


def test_create_repository_git_error() -> None:
    """POST returns 422 when GitService raises GitOperationError."""
    mock_svc = MagicMock()
    mock_svc.create_repository = AsyncMock(
        side_effect=GitOperationError("Failed to clone")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={
                "name": "bad-repo",
                "clone_url": "https://invalid.example/repo.git",
                "branch": "main",
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_create_repository_private_error() -> None:
    """POST returns 400 when GitService/RepositoryService raises PrivateRepositoryNotSupportedError."""
    mock_svc = MagicMock()
    mock_svc.create_repository = AsyncMock(
        side_effect=PrivateRepositoryNotSupportedError()
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories",
            json={
                "name": "private-repo",
                "clone_url": "https://github.com/microsoft/private.git",
                "branch": "main",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Private repositories are not yet supported. Please use a public repository URL."
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — POST /api/v1/repositories/remote-branches
# ---------------------------------------------------------------------------


def test_list_remote_branches_success() -> None:
    """POST /remote-branches returns list of remote branches and default branch."""
    mock_svc = MagicMock()
    mock_svc.list_remote_branches = MagicMock(return_value={
        "branches": [
            {
                "name": "main",
                "ref_type": "branch",
                "commit_sha": "abc1234",
                "commit_message": None,
                "commit_date": None,
            },
            {
                "name": "feature/login",
                "ref_type": "branch",
                "commit_sha": "def5678",
                "commit_message": None,
                "commit_date": None,
            },
        ],
        "default_branch": "main",
    })

    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories/remote-branches",
            json={"clone_url": "https://github.com/example/test-repo.git"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["default_branch"] == "main"
        assert len(data["branches"]) == 2
        assert data["branches"][0]["name"] == "main"
        assert data["branches"][1]["name"] == "feature/login"
    finally:
        app.dependency_overrides.clear()


def test_list_remote_branches_git_error() -> None:
    """POST /remote-branches returns 422 when git operation fails."""
    mock_svc = MagicMock()
    mock_svc.list_remote_branches = MagicMock(
        side_effect=GitOperationError("Remote branch lookup failed")
    )

    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories/remote-branches",
            json={"clone_url": "https://invalid.example/repo.git"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_list_remote_branches_private_error() -> None:
    """POST /remote-branches returns 400 when private repository authentication fails."""
    mock_svc = MagicMock()
    mock_svc.list_remote_branches = MagicMock(
        side_effect=PrivateRepositoryNotSupportedError()
    )

    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories/remote-branches",
            json={"clone_url": "https://github.com/private/repo.git"},
        )
        assert response.status_code == 400
        assert "Private repositories are not yet supported" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_list_remote_branches_empty_url() -> None:
    """POST /remote-branches returns 422 on empty clone_url."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/repositories/remote-branches",
        json={"clone_url": "   "},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — GET /api/v1/repositories
# ---------------------------------------------------------------------------


def test_list_repositories_empty() -> None:
    """GET returns an empty list when no repositories exist."""
    mock_svc = MagicMock()
    mock_svc.list_repositories = AsyncMock(return_value=[])
    mock_svc.count_repositories = AsyncMock(return_value=0)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/repositories")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    finally:
        app.dependency_overrides.clear()


def test_list_repositories_returns_items() -> None:
    """GET returns paginated items and the correct total count."""
    repos = [_make_repo(repo_id=uuid4(), name=f"repo-{i}") for i in range(1, 4)]
    mock_svc = MagicMock()
    mock_svc.list_repositories = AsyncMock(return_value=repos)
    mock_svc.count_repositories = AsyncMock(return_value=3)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/repositories?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — GET /api/v1/repositories/{id}
# ---------------------------------------------------------------------------


def test_get_repository_found() -> None:
    """GET /{id} returns 200 and the matching repository."""
    repo = _make_repo(repo_id=TEST_UUID)
    mock_svc = MagicMock()
    mock_svc.get_repository_or_raise = AsyncMock(return_value=repo)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 200
        assert response.json()["id"] == str(TEST_UUID)
    finally:
        app.dependency_overrides.clear()


def test_get_repository_not_found() -> None:
    """GET /{id} returns 404 when the repository does not exist."""
    mock_svc = MagicMock()
    mock_svc.get_repository_or_raise = AsyncMock(
        side_effect=RepositoryNotFoundError(f"Repository with id={TEST_UUID} does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — DELETE /api/v1/repositories/{id}
# ---------------------------------------------------------------------------


def test_delete_repository_success() -> None:
    """DELETE /{id} returns 204 No Content on success."""
    repo = _make_repo(repo_id=TEST_UUID)
    mock_svc = MagicMock()
    mock_svc.delete_repository_or_raise = AsyncMock(return_value=repo)

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 204
        assert response.content == b""
    finally:
        app.dependency_overrides.clear()


def test_delete_repository_not_found() -> None:
    """DELETE /{id} returns 404 when the repository does not exist."""
    mock_svc = MagicMock()
    mock_svc.delete_repository_or_raise = AsyncMock(
        side_effect=RepositoryNotFoundError(f"Repository with id={TEST_UUID} does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.delete(f"/api/v1/repositories/{TEST_UUID}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_list_repository_languages_success() -> None:
    """GET /{id}/languages returns list of distinct languages."""
    mock_svc = MagicMock()
    mock_svc.list_repository_languages = AsyncMock(return_value=["python", "typescript"])
    mock_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}/languages")
        assert response.status_code == 200
        assert response.json() == ["python", "typescript"]
    finally:
        app.dependency_overrides.clear()


def test_search_repository_files_success() -> None:
    """GET /{id}/files/search returns list of matching files."""
    mock_svc = MagicMock()
    mock_svc.get_repository_or_raise = AsyncMock(return_value=_make_repo())
    mock_db = MagicMock()
    mock_file = MagicMock()
    mock_file.id = 1
    mock_file.path = "src/auth.py"
    mock_file.language = "python"
    mock_file.loc = 50
    mock_file.is_test = False

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_file]
    mock_db.execute = AsyncMock(return_value=mock_res)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}/files/search?query=auth")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["path"] == "src/auth.py"
    finally:
        app.dependency_overrides.clear()


def test_search_repository_files_with_language_filter() -> None:
    """GET /{id}/files/search filters by language parameter."""
    mock_svc = MagicMock()
    mock_svc.get_repository_or_raise = AsyncMock(return_value=_make_repo())
    mock_db = MagicMock()
    mock_file = MagicMock()
    mock_file.id = 1
    mock_file.path = "src/auth.py"
    mock_file.language = "python"
    mock_file.loc = 50
    mock_file.is_test = False

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [mock_file]
    mock_db.execute = AsyncMock(return_value=mock_res)

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}/files/search?query=auth&language=python")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["language"] == "python"
        mock_db.execute.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()


def test_list_repository_refs_endpoint() -> None:
    mock_svc = MagicMock()
    mock_svc.list_repository_refs = AsyncMock(return_value=[
        {
            "name": "main",
            "ref_type": "branch",
            "commit_sha": "abc1234",
            "commit_message": "Initial commit",
            "commit_date": None,
        }
    ])
    mock_db = MagicMock()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}/refs?query=main")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "main"
        assert data[0]["ref_type"] == "branch"
    finally:
        app.dependency_overrides.clear()


