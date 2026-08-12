from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_graph_service
from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeFile, DependencyEdge, Repository
from app.main import app
from app.schemas.graph import GraphResponse
from app.services.graph_service import GraphService

TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class _ExecuteResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.values)


GEN_UUID = UUID("22222222-2222-2222-2222-222222222222")


class _FakeDb:
    def __init__(
        self,
        files: list[CodeFile],
        edges: list[DependencyEdge],
        repo_exists: bool = True,
    ) -> None:
        self.files = files
        self.edges = edges
        self.repo_exists = repo_exists
        self.execute_calls = 0

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and self.repo_exists:
            return Repository(id=object_id, name="repo", clone_url="", status="indexed", active_generation_id=GEN_UUID)
        if model is CodeFile:
            return next((item for item in self.files if item.id == object_id), None)
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        self.execute_calls += 1
        if self.execute_calls == 1:
            if self.repo_exists and len(self.files) > 2:
                return _ExecuteResult(self.files)
            return _ExecuteResult(self.edges)
        if len(self.files) > 2:
            return _ExecuteResult(self.edges)
        return _ExecuteResult(self.files)


def _files() -> list[CodeFile]:
    return [
        CodeFile(
            id=1,
            repository_id=TEST_UUID,
            generation_id=GEN_UUID,
            path="src/auth/token.py",
            language="python",
            content_hash="a",
            loc=20,
            is_test=False,
        ),
        CodeFile(
            id=2,
            repository_id=TEST_UUID,
            generation_id=GEN_UUID,
            path="src/api/routes.py",
            language="python",
            content_hash="b",
            loc=30,
            is_test=False,
        ),
        CodeFile(
            id=3,
            repository_id=TEST_UUID,
            generation_id=GEN_UUID,
            path="tests/test_routes.py",
            language="python",
            content_hash="c",
            loc=10,
            is_test=True,
        ),
    ]


def _edges() -> list[DependencyEdge]:
    return [
        DependencyEdge(
            id=1,
            repository_id=TEST_UUID,
            generation_id=GEN_UUID,
            source_file_id=2,
            target_file_id=1,
            edge_type="import",
            confidence=1.0,
            evidence={"line": 1},
        ),
        DependencyEdge(
            id=2,
            repository_id=TEST_UUID,
            generation_id=GEN_UUID,
            source_file_id=3,
            target_file_id=2,
            edge_type="test_import",
            confidence=0.9,
            evidence={},
        ),
    ]


@pytest.mark.asyncio()
async def test_get_file_neighbors_returns_nodes_and_edges() -> None:
    db = _FakeDb(files=_files()[:2], edges=_edges()[:1])

    response = await GraphService().get_file_neighbors(db, repository_id=TEST_UUID, file_id=1)

    assert {node.path for node in response.nodes} == {
        "src/auth/token.py",
        "src/api/routes.py",
    }
    assert response.edges[0].source_path == "src/api/routes.py"
    assert response.edges[0].target_path == "src/auth/token.py"


@pytest.mark.asyncio()
async def test_get_repository_subgraph_returns_frontend_shape() -> None:
    db = _FakeDb(files=_files(), edges=_edges())

    response = await GraphService().get_repository_subgraph(db, repository_id=TEST_UUID)

    assert len(response.nodes) == 3
    assert len(response.edges) == 2
    assert response.edges[1].edge_type == "test_import"


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_graph_neighbors_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_file_neighbors = AsyncMock(
        return_value=GraphResponse(repository_id=TEST_UUID, nodes=[], edges=[])
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_graph_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/graph/repositories/{TEST_UUID}/file/2/neighbors")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["nodes"] == []
    mock_svc.get_file_neighbors.assert_awaited_once()


def test_graph_subgraph_endpoint_not_found() -> None:
    mock_svc = MagicMock()
    mock_svc.get_repository_subgraph = AsyncMock(
        side_effect=RepositoryNotFoundError(f"Repository with id={TEST_UUID} does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_graph_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/graph/repositories/{TEST_UUID}/subgraph")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
