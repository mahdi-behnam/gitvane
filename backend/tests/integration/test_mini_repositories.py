from pathlib import Path
from typing import Any
from uuid import UUID

import git
import pytest

from app.core.config import settings
from app.db.models import (
    AnalysisRun,
    CodeChunk,
    CodeFile,
    Commit,
    DependencyEdge,
    ImpactPrediction,
    Repository,
    Symbol,
)
from app.schemas.impact import ImpactAnalyzeRequest
from app.services.git_service import GitService
from app.services.impact_service import ImpactService
from app.services.indexing_service import IndexingService

TEST_UUID = UUID("11111111-1111-1111-1111-111111111111")


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class _ExecuteResult:
    def __init__(self, values: list[Any] | None = None) -> None:
        self.values = values or []

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.values)

    def scalar_one(self) -> int:
        return len(self.values)


class _IntegrationDb:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.added: list[Any] = []
        self.next_id = 1
        self.result_queue: list[list[Any]] = []
        self.commits = 0
        self.rollbacks = 0

    async def get(self, model: type[Any], object_id: Any) -> Any:
        if model is Repository and object_id == self.repo.id:
            return self.repo
        return None

    async def execute(self, statement: object) -> _ExecuteResult:
        if self.result_queue:
            return _ExecuteResult(self.result_queue.pop(0))
        return _ExecuteResult()

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id
            self.next_id += 1
        self.added.append(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, obj: Any) -> None:
        pass

    def indexed_rows(
        self,
    ) -> tuple[list[CodeFile], list[Symbol], list[DependencyEdge], list[Commit]]:
        return (
            [item for item in self.added if isinstance(item, CodeFile)],
            [item for item in self.added if isinstance(item, Symbol)],
            [item for item in self.added if isinstance(item, DependencyEdge)],
            [item for item in self.added if isinstance(item, Commit)],
        )

    def queue_index_for_impact(self) -> None:
        code_files, symbols, edges, commits = self.indexed_rows()
        self.result_queue = [code_files, symbols, edges, commits]


class _FakeEmbeddingService:
    async def save_embeddings_for_chunks(
        self,
        db: _IntegrationDb,
        chunks: list[CodeChunk],
        progress_callback: Any = None,
    ) -> int:
        return len(chunks)


class _NoSemanticSearchService:
    async def semantic_search(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("Semantic search is not needed for this integration test")


class _FakeExplanationService:
    async def explain_impact_prediction(self, *args: object) -> str:
        return "deterministic explanation"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit_all(repo: git.Repo, message: str) -> None:
    assert repo.working_tree_dir is not None
    paths = [
        str(path)
        for path in Path(repo.working_tree_dir).rglob("*")
        if path.is_file() and ".git" not in path.parts
    ]
    repo.index.add(paths)
    repo.index.commit(message)


def _init_repo(path: Path) -> git.Repo:
    repo = git.Repo.init(path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "RepoLens Tests")
        config.set_value("user", "email", "tests@example.com")
    return repo


async def _index_and_analyze(
    repo_path: Path,
    changed_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[_IntegrationDb, Any]:
    monkeypatch.setattr(settings, "REPOLENS_WORKSPACE", str(repo_path.parent))
    repo_model = Repository(
        id=TEST_UUID,
        name=repo_path.name,
        clone_url="",
        local_path=repo_path.as_posix(),
        status="ready",
    )
    db = _IntegrationDb(repo_model)
    git_service = GitService()

    await IndexingService(
        git_service=git_service,
        embedding_service=_FakeEmbeddingService(),
    ).index_repository(db=db, repository_id=TEST_UUID, max_commits=10)

    db.queue_index_for_impact()
    response = await ImpactService(
        git_service=git_service,
        semantic_search_service=_NoSemanticSearchService(),
        explanation_service=_FakeExplanationService(),
    ).analyze(
        db,
        ImpactAnalyzeRequest(
            repository_id=TEST_UUID,
            changed_files=[{"path": changed_path}],
            include_explanation=True,
        ),
    )
    return db, response


@pytest.mark.asyncio()
async def test_python_repo_indexes_and_recommends_impacted_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_path = tmp_path / "workspace" / "python_repo"
    repo_path.mkdir(parents=True)
    _write(
        repo_path / "src/auth/token.py",
        "def validate(token: str) -> bool:\n    return bool(token)\n",
    )
    _write(
        repo_path / "src/api/routes.py",
        "from src.auth.token import validate\n\n"
        "def route(token: str) -> bool:\n"
        "    return validate(token)\n",
    )
    _write(
        repo_path / "tests/test_routes.py",
        "from src.api.routes import route\n\n"
        "def test_route() -> None:\n"
        "    assert route('token') is True\n",
    )
    repo = _init_repo(repo_path)
    _commit_all(repo, "Initial Python repo")
    _write(
        repo_path / "src/auth/token.py",
        "def validate(token: str) -> bool:\n    return token.startswith('token')\n",
    )
    _write(
        repo_path / "tests/test_routes.py",
        "from src.api.routes import route\n\n"
        "def test_route() -> None:\n"
        "    assert route('token-1') is True\n",
    )
    _commit_all(repo, "Update token validation and route test")

    db, response = await _index_and_analyze(
        repo_path,
        "src/auth/token.py",
        monkeypatch,
    )

    code_files, _, _, _ = db.indexed_rows()
    assert {item.path for item in code_files} >= {
        "src/auth/token.py",
        "src/api/routes.py",
        "tests/test_routes.py",
    }
    impacted_paths = {item.path for item in response.impacted_files}
    assert "src/api/routes.py" in impacted_paths
    assert "tests/test_routes.py" in impacted_paths
    assert response.recommended_tests[0].path == "tests/test_routes.py"
    assert any(isinstance(item, AnalysisRun) for item in db.added)
    assert any(isinstance(item, ImpactPrediction) for item in db.added)


@pytest.mark.asyncio()
async def test_typescript_repo_indexes_and_recommends_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_path = tmp_path / "workspace" / "typescript_repo"
    repo_path.mkdir(parents=True)
    _write(
        repo_path / "src/auth/token.ts",
        "export function validate(token: string): boolean {\n"
        "  return token.length > 0;\n"
        "}\n",
    )
    _write(
        repo_path / "src/api/routes.ts",
        "import { validate } from '../auth/token';\n\n"
        "export function route(token: string): boolean {\n"
        "  return validate(token);\n"
        "}\n",
    )
    _write(
        repo_path / "src/auth/token.test.ts",
        "import { validate } from './token';\n\n"
        "test('validates token', () => {\n"
        "  expect(validate('token')).toBe(true);\n"
        "});\n",
    )
    repo = _init_repo(repo_path)
    _commit_all(repo, "Initial TypeScript repo")
    _write(
        repo_path / "src/auth/token.ts",
        "export function validate(token: string): boolean {\n"
        "  return token.startsWith('token');\n"
        "}\n",
    )
    _write(
        repo_path / "src/auth/token.test.ts",
        "import { validate } from './token';\n\n"
        "test('validates token', () => {\n"
        "  expect(validate('token-1')).toBe(true);\n"
        "});\n",
    )
    _commit_all(repo, "Update token validation and test")

    db, response = await _index_and_analyze(
        repo_path,
        "src/auth/token.ts",
        monkeypatch,
    )

    code_files, _, _, _ = db.indexed_rows()
    assert {item.path for item in code_files} >= {
        "src/auth/token.ts",
        "src/api/routes.ts",
        "src/auth/token.test.ts",
    }
    assert "src/api/routes.ts" in {item.path for item in response.impacted_files}
    assert response.recommended_tests[0].path == "src/auth/token.test.ts"
    assert response.llm_explanation == "deterministic explanation"
