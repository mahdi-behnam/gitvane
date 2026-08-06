from types import SimpleNamespace
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_risk_service
from app.db.models import CodeChunk, CodeFile, Commit, DependencyEdge, Repository
from app.main import app
from app.schemas.risk import RepositoryRiskResponse
from app.services.risk_service import RiskService

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

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and self.repo_exists:
            return Repository(id=object_id, name="repo", clone_url="", status="indexed")
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.results.pop(0))


def test_risk_service_scores_file_components() -> None:
    code_file = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )
    risk = RiskService().score_file(
        code_file,
        fan_in=12,
        fan_out=2,
        churn=15,
        bugfix_churn=4,
        complexity=0.7,
    )
    assert risk.score > 0.6
    assert "High fan-in" in risk.reasons
    assert "Frequently changed" in risk.reasons


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
    payment = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )
    helpers = CodeFile(
        id=2,
        repository_id=TEST_UUID,
        path="src/core/helpers.py",
        language="python",
        content_hash="def",
        loc=50,
        is_test=False,
    )
    tests = CodeFile(
        id=3,
        repository_id=TEST_UUID,
        path="tests/test_payment.py",
        language="python",
        content_hash="ghi",
        loc=80,
        is_test=True,
    )
    edge = DependencyEdge(
        id=1,
        repository_id=TEST_UUID,
        source_file_id=2,
        target_file_id=1,
        edge_type="import",
    )
    commit = Commit(
        id=1,
        repository_id=TEST_UUID,
        sha="c1",
        message="fix payment crash",
        changed_files=[{"path": "src/core/payment.py"}],
    )
    chunk = CodeChunk(
        id=1,
        repository_id=TEST_UUID,
        file_id=1,
        chunk_type="function",
        start_line=1,
        end_line=100,
        content_hash="abc",
        text="def process_payment():\n" + "    pass\n" * 100,
    )
    db = _FakeDb(
        code_files=[payment, helpers, tests],
        edges=[edge],
        commits=[commit],
        chunks=[chunk],
    )

    response = await RiskService().get_repository_file_risks(
        db,
        repository_id=TEST_UUID,
        include_tests=False,
    )

    assert response.files[0].path == "src/core/payment.py"
    assert response.files[0].risk_score > 0
    assert all(not item.path.startswith("tests/") for item in response.files)
    assert "mean_risk_score" in response.metadata
    assert isinstance(response.metadata["mean_risk_score"], float)


@pytest.mark.asyncio()
async def test_repository_risk_path_search_and_mean_risk_score() -> None:
    service = RiskService()
    payment = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )
    helpers = CodeFile(
        id=2,
        repository_id=TEST_UUID,
        path="src/utils/helpers.py",
        language="python",
        content_hash="def",
        loc=50,
        is_test=False,
    )
    db = _FakeDb(
        code_files=[payment, helpers],
        edges=[],
        commits=[],
        chunks=[],
    )

    payment_risk = service.score_file(payment)
    helpers_risk = service.score_file(helpers)
    expected_mean = round((payment_risk.score + helpers_risk.score) / 2, 4)

    response = await service.get_repository_file_risks(
        db,
        repository_id=TEST_UUID,
        path_search="core",
    )

    assert len(response.files) == 1
    assert response.files[0].path == "src/core/payment.py"
    assert response.metadata["path_search"] == "core"
    assert response.metadata["mean_risk_score"] == expected_mean


@pytest.mark.asyncio()
async def test_repository_risk_path_search_unmatched_reflects_true_repo_average() -> None:
    service = RiskService()
    payment = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        path="src/core/payment.py",
        language="python",
        content_hash="abc",
        loc=400,
        is_test=False,
    )
    helpers = CodeFile(
        id=2,
        repository_id=TEST_UUID,
        path="src/utils/helpers.py",
        language="python",
        content_hash="def",
        loc=50,
        is_test=False,
    )
    db = _FakeDb(
        code_files=[payment, helpers],
        edges=[],
        commits=[],
        chunks=[],
    )

    payment_risk = service.score_file(payment)
    helpers_risk = service.score_file(helpers)
    expected_mean = round((payment_risk.score + helpers_risk.score) / 2, 4)

    response = await service.get_repository_file_risks(
        db,
        repository_id=TEST_UUID,
        path_search="nonexistent",
    )

    assert len(response.files) == 0
    assert response.metadata["path_search"] == "nonexistent"
    assert response.metadata["mean_risk_score"] == expected_mean
    assert response.metadata["mean_risk_score"] > 0


@pytest.mark.asyncio()
async def test_repository_risk_raises_for_missing_repo() -> None:
    db = _FakeDb([], [], [], [], repo_exists=False)

    with pytest.raises(Exception, match=r"Repository with id="):
        await RiskService().get_repository_file_risks(db, repository_id=TEST_UUID)


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


def test_risk_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_repository_file_risks = AsyncMock(
        return_value=RepositoryRiskResponse(
            repository_id=TEST_UUID,
            files=[],
            metadata={"top_k": 20, "mean_risk_score": 0.0},
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_risk_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/risk/repositories/{TEST_UUID}/files?top_k=5&path_search=payment")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["repository_id"] == str(TEST_UUID)
    mock_svc.get_repository_file_risks.assert_awaited_once()
    _, kwargs = mock_svc.get_repository_file_risks.call_args
    assert kwargs.get("path_search") == "payment"
