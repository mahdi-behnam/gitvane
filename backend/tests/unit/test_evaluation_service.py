from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest

from app.db.models import (
    CodeFile,
    Commit,
    DependencyEdge,
    EvaluationResult,
    EvaluationRun,
    Repository,
)
from app.schemas.evaluation import EvaluationRunRequest
from app.schemas.search import SemanticSearchResponse, SemanticSearchResult
from app.services.evaluation_service import EvaluationService

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
        repo: Repository,
        code_files: list[CodeFile],
        edges: list[DependencyEdge],
        commits: list[Commit],
    ) -> None:
        self.repo = repo
        self.results = [commits, code_files, edges]
        self.added: list[Any] = []
        self.next_id = 1
        self.committed = False

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and object_id == self.repo.id:
            return self.repo
        if model is EvaluationRun:
            return next(
                (item for item in self.added if isinstance(item, EvaluationRun)),
                None,
            )
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        if self.results:
            return _ExecuteResult(self.results.pop(0))
        eval_results = [item for item in self.added if isinstance(item, EvaluationResult)]
        return _ExecuteResult(eval_results)

    def add(self, instance: Any) -> None:
        if hasattr(instance, "id") and getattr(instance, "id", None) is None:
            setattr(instance, "id", self.next_id)
            self.next_id += 1
        self.added.append(instance)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass

    async def refresh(self, instance: Any) -> None:
        pass


class _FakeSemanticSearchService:
    async def semantic_search(
        self,
        db: _FakeDb,
        repository_id: UUID | Any,
        query: str,
        top_k: int = 20,
    ) -> SemanticSearchResponse:
        return SemanticSearchResponse(
            repository_id=repository_id,
            query=query,
            results=[
                SemanticSearchResult(
                    path="src/api/routes.py",
                    symbol="routes",
                    start_line=1,
                    end_line=10,
                    score=0.8,
                    snippet="routes",
                )
            ]
        )


GEN_UUID = UUID("22222222-2222-2222-2222-222222222222")


def _fixture() -> tuple[Repository, list[CodeFile], list[DependencyEdge], list[Commit]]:
    repo = Repository(id=TEST_UUID, name="repo", clone_url="", status="indexed", active_generation_id=GEN_UUID)
    token = CodeFile(
        id=1,
        repository_id=TEST_UUID,
        generation_id=GEN_UUID,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
    )
    routes = CodeFile(
        id=2,
        repository_id=TEST_UUID,
        generation_id=GEN_UUID,
        path="src/api/routes.py",
        language="python",
        content_hash="b",
    )
    edge = DependencyEdge(
        repository_id=TEST_UUID,
        generation_id=GEN_UUID,
        source_file_id=2,
        target_file_id=1,
        edge_type="import",
    )
    commit = Commit(
        repository_id=TEST_UUID,
        sha="abc",
        author_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        changed_files=[
            {"path": "src/auth/token.py"},
            {"path": "src/api/routes.py"},
        ],
        message="Update auth route",
    )
    return repo, [token, routes], [edge], [commit]


@pytest.mark.asyncio()
async def test_run_evaluation_computes_method_summaries() -> None:
    repo, files, edges, commits = _fixture()
    db = _FakeDb(repo, files, edges, commits)
    service = EvaluationService(semantic_search_service=_FakeSemanticSearchService())

    response = await service.run_evaluation(
        db,
        EvaluationRunRequest(
            repository_id=TEST_UUID,
            methods=["dependency_only", "semantic_only", "cochange_only", "hybrid"],
            k_values=[1],
        ),
    )

    assert response.status == "completed"
    assert response.summary["evaluated_commits"] == 1
    assert response.summary["methods"]["dependency_only"]["recall_at_1"] == 1.0
    assert response.summary["methods"]["semantic_only"]["precision_at_1"] == 1.0
    assert any(isinstance(item, EvaluationResult) for item in db.added)
    assert db.committed is True


@pytest.mark.asyncio()
async def test_evaluation_report_mentions_current_index_limitation() -> None:
    repo, files, edges, commits = _fixture()
    db = _FakeDb(repo, files, edges, commits)
    service = EvaluationService(semantic_search_service=_FakeSemanticSearchService())
    run_response = await service.run_evaluation(
        db,
        EvaluationRunRequest(repository_id=TEST_UUID, methods=["dependency_only"], k_values=[1]),
    )

    report = await service.get_report(db, run_response.evaluation_run_id)

    assert "current indexed graph approximation" in report.markdown
    assert "dependency_only" in report.markdown
