from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_db,
    get_semantic_search_service,
    get_test_recommendation_service,
)
from app.core.errors import RepositoryNotFoundError
from app.db.models import CodeFile, Commit, DependencyEdge, Repository
from app.main import app
from app.schemas.impact import ChangedFileInput
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult
from app.schemas.tests import TestRecommendationResponse as RecommendationResponse
from app.services.test_recommendation_service import TestRecommendationService

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
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
        repo_exists: bool = True,
    ) -> None:
        self.results = [commits, code_files, edges]
        self.repo_exists = repo_exists

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and self.repo_exists:
            return Repository(id=object_id, name="repo", clone_url="", status="indexed", active_generation_id=GEN_UUID)
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.results.pop(0))


class _FakeSemanticSearchService:
    async def semantic_search(
        self,
        db: _FakeDb,
        repository_id: UUID | Any,
        query: str,
        top_k: int = 50,
    ) -> SemanticSearchResponse:
        return SemanticSearchResponse(
            repository_id=repository_id,
            query=query,
            results=[
                SemanticSearchResult(
                    path="tests/test_auth_flow.py",
                    symbol="test_auth_flow",
                    start_line=1,
                    end_line=10,
                    score=0.74,
                    snippet="auth flow",
                )
            ]
        )


def test_recommends_tests_by_import_edge() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="tests/test_token.py",
        language="python",
        content_hash="b",
        is_test=True,
    )
    edge = DependencyEdge(
        repository_id=1,
        source_file_id=2,
        target_file_id=1,
        edge_type="test_import",
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.py"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[edge],
    )

    assert recommendations[0].path == "tests/test_token.py"
    assert recommendations[0].score == 0.95
    assert recommendations[0].linked_files == ["src/auth/token.py"]


def test_recommends_tests_by_naming_convention() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.ts",
        language="typescript",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="src/auth/token.test.ts",
        language="typescript",
        content_hash="b",
        is_test=True,
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.ts"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[],
    )

    assert recommendations[0].path == "src/auth/token.test.ts"
    assert recommendations[0].score == 0.85


def test_recommends_tests_by_directory_proximity() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="src/auth/test_session.py",
        language="python",
        content_hash="b",
        is_test=True,
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.py"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[],
    )

    assert recommendations[0].path == "src/auth/test_session.py"
    assert recommendations[0].score == 0.55


def test_recommends_tests_by_cochange_history() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="tests/test_auth_flow.py",
        language="python",
        content_hash="b",
        is_test=True,
    )
    commits = [
        {
            "changed_files": [
                {"path": "src/auth/token.py"},
                {"path": "tests/test_auth_flow.py"},
            ]
        }
    ]

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.py"},
        impacted_paths=set(),
        code_files=[source, test],
        dependency_edges=[],
        commits=commits,
    )

    assert recommendations[0].path == "tests/test_auth_flow.py"
    assert recommendations[0].score == 0.75


def test_recommends_tests_by_semantic_score() -> None:
    test = CodeFile(
        id=2,
        repository_id=1,
        path="tests/test_auth_flow.py",
        language="python",
        content_hash="b",
        is_test=True,
    )

    recommendations = TestRecommendationService().recommend_tests(
        changed_paths={"src/auth/token.py"},
        impacted_paths=set(),
        code_files=[test],
        dependency_edges=[],
        semantic_scores={"tests/test_auth_flow.py": 0.72},
    )

    assert recommendations[0].path == "tests/test_auth_flow.py"
    assert recommendations[0].score == 0.72


@pytest.mark.asyncio()
async def test_recommend_for_repository_loads_indexed_data() -> None:
    source = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        generation_id=GEN_UUID,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=TEST_UUID,
        generation_id=GEN_UUID,
        path="tests/test_auth_flow.py",
        language="python",
        content_hash="b",
        is_test=True,
    )
    db = _FakeDb(code_files=[source, test], edges=[], commits=[])

    response = await TestRecommendationService().recommend_for_repository(
        db=db,
        repository_id=TEST_UUID,
        changed_files=[ChangedFileInput(path="src/auth/token.py")],
        semantic_search_service=_FakeSemanticSearchService(),
    )

    assert response.repository_id == TEST_UUID
    assert response.recommended_tests[0].path == "tests/test_auth_flow.py"
    assert response.recommended_tests[0].score == 0.74


@pytest.mark.asyncio()
async def test_recommend_for_repository_raises_for_missing_repo() -> None:
    db = _FakeDb(code_files=[], edges=[], commits=[], repo_exists=False)

    with pytest.raises(RepositoryNotFoundError):
        await TestRecommendationService().recommend_for_repository(
            db=db,
            repository_id=TEST_UUID,
            changed_files=[ChangedFileInput(path="src/auth/token.py")],
        )


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_test_recommendation_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.recommend_for_repository = AsyncMock(
        return_value=RecommendationResponse(
            repository_id=TEST_UUID,
            changed_files=[ChangedFileInput(path="src/auth/token.py")],
            recommended_tests=[],
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_test_recommendation_service] = lambda: mock_svc
    app.dependency_overrides[get_semantic_search_service] = lambda: MagicMock()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/tests/recommend",
            json={
                "repository_id": str(TEST_UUID),
                "changed_files": [{"path": "src/auth/token.py"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["repository_id"] == str(TEST_UUID)
    mock_svc.recommend_for_repository.assert_awaited_once()


def test_test_recommendation_endpoint_not_found() -> None:
    mock_svc = MagicMock()
    mock_svc.recommend_for_repository = AsyncMock(
        side_effect=RepositoryNotFoundError(f"Repository with id={TEST_UUID} does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_test_recommendation_service] = lambda: mock_svc
    app.dependency_overrides[get_semantic_search_service] = lambda: MagicMock()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/tests/recommend",
            json={
                "repository_id": str(TEST_UUID),
                "changed_files": [{"path": "src/auth/token.py"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
