from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_indexing_service
from app.core.errors import GitOperationError, RepositoryNotFoundError
from app.main import app
from app.schemas.indexing import IndexRepositoryResponse, IndexStatusResponse


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_index_repository_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.index_repository = AsyncMock(
        return_value=IndexRepositoryResponse(
            repository_id=1,
            status="indexed",
            current_ref="abc123",
            indexed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            files_indexed=2,
            files_skipped=1,
            symbols_indexed=3,
            chunks_indexed=3,
            embeddings_indexed=3,
            dependency_edges_indexed=1,
            commits_indexed=4,
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_indexing_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/repositories/1/index",
            json={"ref": "main", "max_commits": 10},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    mock_svc.index_repository.assert_awaited_once()


def test_index_repository_endpoint_not_found() -> None:
    mock_svc = MagicMock()
    mock_svc.index_repository = AsyncMock(
        side_effect=RepositoryNotFoundError("Repository with id=99 does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_indexing_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post("/api/v1/repositories/99/index", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_index_repository_endpoint_git_error() -> None:
    mock_svc = MagicMock()
    mock_svc.index_repository = AsyncMock(
        side_effect=GitOperationError("Failed to open repository")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_indexing_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post("/api/v1/repositories/1/index", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_index_status_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_index_status = AsyncMock(
        return_value=IndexStatusResponse(
            repository_id=1,
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
        response = client.get("/api/v1/repositories/1/index/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["file_count"] == 2
    mock_svc.get_index_status.assert_awaited_once()
