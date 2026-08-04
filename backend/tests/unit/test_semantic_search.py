from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_semantic_search_service
from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeChunk, CodeFile, Repository, Symbol
from app.main import app
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult
from app.services.semantic_search_service import SemanticSearchService

TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


class _FakeEmbeddingService:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2]


class _ExecuteResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return self.rows


class _FakeDb:
    def __init__(self, rows: list[tuple[Any, ...]], repo_exists: bool = True) -> None:
        self.rows = rows
        self.repo_exists = repo_exists

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and self.repo_exists:
            return Repository(id=object_id, name="repo", clone_url="", status="indexed")
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.rows)


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


@pytest.mark.asyncio()
async def test_semantic_search_returns_ranked_results() -> None:
    chunk = CodeChunk(
        id=1,
        repository_id=TEST_UUID,
        file_id=1,
        text="path: src/auth/token.py\nsymbol: validate\n\nvalidate token expiry",
        start_line=10,
        end_line=20,
        content_hash="abc",
        chunk_type="function",
    )
    code_file = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        path="src/auth/token.py",
        language="python",
        content_hash="abc",
    )
    symbol = Symbol(
        id=1,
        repository_id=TEST_UUID,
        file_id=1,
        qualified_name="validate",
        simple_name="validate",
        symbol_type="function",
        start_line=10,
        end_line=20,
        content_hash="abc",
    )
    db = _FakeDb(rows=[(chunk, code_file, symbol, 0.17)])
    service = SemanticSearchService(_FakeEmbeddingService())

    response = await service.semantic_search(db, TEST_UUID, "jwt expiration", top_k=5)

    assert response.results[0].path == "src/auth/token.py"
    assert response.results[0].language == "python"
    assert response.results[0].symbol == "validate"
    assert response.results[0].score == 0.83
    assert "validate token expiry" in response.results[0].snippet



@pytest.mark.asyncio()
async def test_semantic_search_raises_for_missing_repository() -> None:
    service = SemanticSearchService(_FakeEmbeddingService())

    with pytest.raises(RepositoryNotFoundError):
        await service.semantic_search(_FakeDb(rows=[], repo_exists=False), TEST_UUID, "auth")


def test_semantic_search_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.semantic_search = AsyncMock(
        return_value=SemanticSearchResponse(
            results=[
                SemanticSearchResult(
                    path="src/auth/token.py",
                    symbol="validate",
                    start_line=10,
                    end_line=20,
                    score=0.83,
                    snippet="validate token expiry",
                )
            ]
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_semantic_search_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"repository_id": str(TEST_UUID), "query": "jwt expiration", "top_k": 5},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["results"][0]["path"] == "src/auth/token.py"
    mock_svc.semantic_search.assert_awaited_once()


def test_semantic_search_endpoint_not_found() -> None:
    mock_svc = MagicMock()
    mock_svc.semantic_search = AsyncMock(
        side_effect=RepositoryNotFoundError(f"Repository with id={TEST_UUID} does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_semantic_search_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/search/semantic",
            json={"repository_id": str(TEST_UUID), "query": "auth", "top_k": 5},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
