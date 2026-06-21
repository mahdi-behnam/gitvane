from datetime import datetime, timezone
from typing import Any

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
        self.results = [code_files, edges, commits]
        self.added: list[Any] = []
        self.next_id = 1
        self.committed = False

    async def get(self, model: type[Any], object_id: int) -> Any:
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
        return _ExecuteResult(
            [item for item in self.added if isinstance(item, EvaluationResult)]
        )

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
        pass

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
                    symbol=None,
                    start_line=1,
                    end_line=2,
                    score=0.8,
                    snippet="routes",
                )
            ]
        )


def _fixture() -> tuple[Repository, list[CodeFile], list[DependencyEdge], list[Commit]]:
    repo = Repository(id=1, name="repo", clone_url="", status="indexed")
    token = CodeFile(
        id=1,
        repository_id=1,
        path="src/auth/token.py",
        language="python",
        content_hash="a",
    )
    routes = CodeFile(
        id=2,
        repository_id=1,
        path="src/api/routes.py",
        language="python",
        content_hash="b",
    )
    edge = DependencyEdge(
        repository_id=1,
        source_file_id=2,
        target_file_id=1,
        edge_type="import",
    )
    commit = Commit(
        repository_id=1,
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
            repository_id=1,
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
        EvaluationRunRequest(repository_id=1, methods=["dependency_only"], k_values=[1]),
    )

    report = await service.get_report(db, run_response.evaluation_run_id)

    assert "current indexed graph approximation" in report.markdown
    assert "dependency_only" in report.markdown
