from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_impact_service
from app.db.models import (
    CodeFile,
    Commit,
    DependencyEdge,
    ImpactPrediction,
    Repository,
    Symbol,
)
from app.main import app
from app.schemas.impact import ImpactAnalyzeRequest
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult
from app.services.impact_service import ImpactService


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


class _FakeDb:
    def __init__(
        self,
        repo: Repository,
        code_files: list[CodeFile],
        symbols: list[Symbol],
        edges: list[DependencyEdge],
        commits: list[Commit],
    ) -> None:
        self.repo = repo
        self.results = [code_files, symbols, edges, commits]
        self.added: list[Any] = []
        self.next_id = 100
        self.committed = False
        self.rolled_back = False

    async def get(self, model: type[Any], object_id: int) -> Any:
        if model is Repository and object_id == self.repo.id:
            return self.repo
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.results.pop(0) if self.results else [])

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id
            self.next_id += 1
        self.added.append(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj: Any) -> None:
        pass


class _FakeSemanticSearchService:
    async def semantic_search(
        self,
        db: _FakeDb,
        repository_id: int,
        query: str,
        top_k: int,
    ) -> SemanticSearchResponse:
        return SemanticSearchResponse(
            results=[
                SemanticSearchResult(
                    path="src/api/routes.py",
                    symbol="route",
                    start_line=1,
                    end_line=3,
                    score=0.75,
                    snippet="route calls token",
                )
            ]
        )


class _FakeExplanationService:
    async def explain_impact_prediction(self, *args: object) -> str:
        return "deterministic explanation"


def _indexed_fixture() -> tuple[
    Repository,
    list[CodeFile],
    list[Symbol],
    list[DependencyEdge],
    list[Commit],
]:
    repo = Repository(id=1, name="repo", clone_url="", status="indexed")
    token = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
        loc=20,
        is_test=False,
    )
    routes = CodeFile(
        id=2,
        repository_id=1,
        path="src/api/routes.py",
        language="python",
        content_hash="b",
        loc=30,
        is_test=False,
    )
    tests = CodeFile(
        id=3,
        repository_id=1,
        path="tests/test_routes.py",
        language="python",
        content_hash="c",
        loc=10,
        is_test=True,
    )
    unrelated = CodeFile(
        id=4,
        repository_id=1,
        path="src/unrelated.py",
        language="python",
        content_hash="d",
        loc=5,
        is_test=False,
    )
    symbols = [
        Symbol(
            id=1,
            repository_id=1,
            file_id=1,
            qualified_name="validate_token",
            simple_name="validate_token",
            symbol_type="function",
            start_line=5,
            end_line=12,
            content_hash="s",
        )
    ]
    edges = [
        DependencyEdge(
            repository_id=1,
            source_file_id=2,
            target_file_id=1,
            edge_type="import",
        ),
        DependencyEdge(
            repository_id=1,
            source_file_id=3,
            target_file_id=2,
            edge_type="test_import",
        ),
    ]
    commits = [
        Commit(
            repository_id=1,
            sha="abc",
            changed_files=[
                {"path": "src/auth/token.py"},
                {"path": "src/api/routes.py"},
            ],
            message="Fix auth route",
        )
    ]
    return repo, [token, routes, tests, unrelated], symbols, edges, commits


@pytest.mark.asyncio()
async def test_impact_service_ranks_dependency_and_test_candidates() -> None:
    repo, code_files, symbols, edges, commits = _indexed_fixture()
    db = _FakeDb(repo, code_files, symbols, edges, commits)
    service = ImpactService(
        git_service=MagicMock(),
        semantic_search_service=_FakeSemanticSearchService(),
        explanation_service=_FakeExplanationService(),
    )

    response = await service.analyze(
        db,
        ImpactAnalyzeRequest(
            repository_id=1,
            changed_files=[
                {
                    "path": "src/auth/token.py",
                    "change_type": "modified",
                    "changed_lines": [(6, 8)],
                }
            ],
            include_explanation=True,
        ),
    )

    assert response.analysis_run_id == 100
    assert response.changed_symbols[0].qualified_name == "validate_token"
    assert response.impacted_files[0].path == "src/api/routes.py"
    assert response.impacted_files[0].component_scores["dependency"] == 1.0
    assert any(item.path == "tests/test_routes.py" for item in response.impacted_files)
    assert response.recommended_tests[0].path == "tests/test_routes.py"
    assert response.llm_explanation == "deterministic explanation"
    assert db.committed is True
    assert any(isinstance(item, ImpactPrediction) for item in db.added)


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_impact_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.analyze = AsyncMock(
        return_value={
            "analysis_run_id": 1,
            "repository_id": 1,
            "base_ref": None,
            "head_ref": None,
            "changed_files": [
                {"path": "src/auth/token.py", "change_type": "modified"}
            ],
            "changed_symbols": [],
            "impacted_files": [],
            "recommended_tests": [],
            "risk_summary": {"highest_risk_files": []},
            "llm_explanation": None,
        }
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_impact_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/impact/analyze",
            json={
                "repository_id": 1,
                "changed_files": [{"path": "src/auth/token.py"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["analysis_run_id"] == 1
