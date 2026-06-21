from types import SimpleNamespace
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_risk_service
from app.db.models import CodeChunk, CodeFile, Commit, DependencyEdge, Repository
from app.main import app
from app.schemas.risk import RepositoryRiskResponse
from app.services.risk_service import RiskService


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
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
        chunks: list[CodeChunk],
        repo_exists: bool = True,
    ) -> None:
        self.results = [code_files, edges, commits, chunks]
        self.repo_exists = repo_exists

    async def get(self, model: type[Any], object_id: int) -> Any:
        if model is Repository and self.repo_exists:
            return Repository(id=object_id, name="repo", clone_url="", status="indexed")
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.results.pop(0))


def test_risk_service_scores_file_components() -> None:
    code_file = CodeFile(
        id=1,
        repository_id=1,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )

    risk = RiskService().score_file(
        code_file,
        fan_in=8,
        fan_out=3,
        churn=12,
        bugfix_churn=2,
        complexity=0.7,
    )

    assert risk.path == "src/core/payment.py"
    assert 0.0 < risk.score <= 1.0
    assert risk.components["fan_in"] == 0.8
    assert risk.components["complexity"] == 0.7
    assert "High fan-in" in risk.reasons


def test_risk_service_counts_bugfix_churn() -> None:
    commits = [
        SimpleNamespace(
            message="Fix payment regression",
            changed_files=[{"path": "src/core/payment.py"}],
        ),
        SimpleNamespace(
            message="Refactor names",
            changed_files=[{"path": "src/core/payment.py"}],
        ),
    ]

    assert RiskService().bugfix_churn_for_file("src/core/payment.py", commits) == 1


@pytest.mark.asyncio()
async def test_repository_risk_ranks_indexed_files() -> None:
    source = CodeFile(
        id=1,
        repository_id=1,
        path="src/core/payment.py",
        language="python",
        content_hash="a",
        loc=400,
        is_test=False,
    )
    test = CodeFile(
        id=2,
        repository_id=1,
        path="tests/test_payment.py",
        language="python",
        content_hash="b",
        loc=30,
        is_test=True,
    )
    edge = DependencyEdge(
        repository_id=1,
        source_file_id=2,
        target_file_id=1,
        edge_type="test_import",
    )
    commit = Commit(
        repository_id=1,
        sha="abc",
        message="Fix payment bug",
        changed_files=[{"path": "src/core/payment.py"}],
    )
    chunk = CodeChunk(
        id=1,
        repository_id=1,
        file_id=1,
        chunk_type="function",
        text="def pay(x):\n    if x:\n        return x\n",
        start_line=1,
        end_line=3,
        content_hash="c",
    )
    db = _FakeDb(
        code_files=[source, test],
        edges=[edge],
        commits=[commit],
        chunks=[chunk],
    )

    response = await RiskService().get_repository_file_risks(
        db,
        repository_id=1,
        include_tests=False,
    )

    assert response.files[0].path == "src/core/payment.py"
    assert response.files[0].risk_score > 0
    assert all(not item.path.startswith("tests/") for item in response.files)


@pytest.mark.asyncio()
async def test_repository_risk_raises_for_missing_repo() -> None:
    db = _FakeDb([], [], [], [], repo_exists=False)

    with pytest.raises(Exception, match="Repository with id=99"):
        await RiskService().get_repository_file_risks(db, repository_id=99)


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_risk_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_repository_file_risks = AsyncMock(
        return_value=RepositoryRiskResponse(
            repository_id=1,
            files=[],
            metadata={"top_k": 20},
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_risk_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/risk/repositories/1/files?top_k=5")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["repository_id"] == 1
    mock_svc.get_repository_file_risks.assert_awaited_once()
