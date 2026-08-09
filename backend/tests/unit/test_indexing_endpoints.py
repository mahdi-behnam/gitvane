from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_indexing_service
from app.core.errors import GitOperationError, RepositoryNotFoundError
from app.core.security_utils import create_access_token
from app.main import app
from app.schemas.indexing import IndexRepositoryResponse, IndexStatusResponse

TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


@patch("app.api.v1.endpoints.indexing.SessionLocal")
@patch("app.api.v1.endpoints.indexing.IndexingService")
def test_index_repository_endpoint_success(
    mock_indexing_service_cls: MagicMock, mock_session_local_cls: MagicMock
) -> None:
    mock_db = MagicMock()
    mock_repo = MagicMock()
    mock_repo.id = TEST_UUID
    mock_repo.status = "ready"
    mock_db.get = AsyncMock(return_value=mock_repo)
    mock_db.commit = AsyncMock()

    async def mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db

    mock_async_db = MagicMock()
    mock_session_local_cls.return_value.__aenter__.return_value = mock_async_db

    mock_svc_instance = mock_indexing_service_cls.return_value
    mock_svc_instance.index_repository = AsyncMock()

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/repositories/{TEST_UUID}/index",
            json={"ref": "main"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "indexing"
    assert response.json()["repository_id"] == str(TEST_UUID)

    assert mock_repo.status == "indexing"
    mock_db.commit.assert_awaited_once()

    mock_session_local_cls.assert_called_once()
    mock_svc_instance.index_repository.assert_awaited_once_with(
        db=mock_async_db,
        repository_id=TEST_UUID,
        ref="main",
    )


def test_index_repository_endpoint_not_found() -> None:
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=None)

    async def mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db
    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/repositories/{TEST_UUID}/index", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@patch("app.api.v1.endpoints.indexing.SessionLocal")
@patch("app.api.v1.endpoints.indexing.IndexingService")
def test_index_repository_endpoint_git_error(
    mock_indexing_service_cls: MagicMock, mock_session_local_cls: MagicMock
) -> None:
    mock_db = MagicMock()
    mock_repo = MagicMock()
    mock_repo.id = TEST_UUID
    mock_repo.status = "ready"
    mock_db.get = AsyncMock(return_value=mock_repo)
    mock_db.commit = AsyncMock()

    async def mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db

    mock_async_db = MagicMock()
    mock_async_db.get = AsyncMock(return_value=mock_repo)
    mock_async_db.commit = AsyncMock()
    mock_session_local_cls.return_value.__aenter__.return_value = mock_async_db

    mock_svc_instance = mock_indexing_service_cls.return_value
    mock_svc_instance.index_repository = AsyncMock(
        side_effect=GitOperationError("Failed to open repository")
    )

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/repositories/{TEST_UUID}/index", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["status"] == "indexing"

    mock_svc_instance.index_repository.assert_awaited_once()


def test_index_status_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_index_status = AsyncMock(
        return_value=IndexStatusResponse(
            repository_id=TEST_UUID,
            status="indexed",
            current_ref="abc123",
            last_indexed_commit="abc123",
            indexed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            file_count=2,
            symbol_count=3,
            chunk_count=3,
            dependency_edge_count=1,
            commit_count=4,
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_indexing_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/repositories/{TEST_UUID}/index/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["file_count"] == 2
    mock_svc.get_index_status.assert_awaited_once()


def test_index_events_unauthenticated() -> None:
    """Unauthenticated access to SSE stream should return 401 Unauthorized."""
    client = TestClient(app)
    response = client.get(f"/api/v1/repositories/{TEST_UUID}/index/events")
    assert response.status_code == 401


def test_index_events_authenticated_valid_token() -> None:
    """Authenticated access with valid token passes auth check."""
    token = create_access_token(subject=1)
    mock_svc = MagicMock()
    mock_repo = MagicMock()
    mock_repo.id = TEST_UUID
    mock_repo.status = "ready"
    mock_repo.repo_metadata = {}
    mock_svc.get_repository_or_raise = AsyncMock(return_value=mock_repo)

    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.is_active = True
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=mock_res)

    from app.api.deps import get_repository_service
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_repository_service] = lambda: mock_svc

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/repositories/{TEST_UUID}/index/events",
            params={"token": token},
        )
        assert response.status_code == 200
        call_args = mock_svc.get_repository_or_raise.await_args
        assert call_args.args[1] == TEST_UUID
        assert call_args.kwargs.get("owner_id") == 1
    finally:
        app.dependency_overrides.clear()
