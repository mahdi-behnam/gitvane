from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.db.models import CodeChunk, CodeFile, DependencyEdge, Repository, Symbol
from app.services.indexing_service import IndexingService


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


class _FakeDb:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.added: list[Any] = []
        self.next_id = 1
        self.committed = False
        self.rolled_back = False

    async def get(self, model: type[Any], object_id: int) -> Any:
        if model is Repository and object_id == self.repo.id:
            return self.repo
        return None

    async def execute(self, statement: Any) -> _ExecuteResult:
        return _ExecuteResult([])

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


@pytest.fixture()
def repo_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "workspace"
    repo_path = workspace / "repo_1"
    repo_path.mkdir(parents=True)
    monkeypatch.setattr(settings, "REPOLENS_WORKSPACE", str(workspace))
    return repo_path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.asyncio()
async def test_index_repository_persists_core_index_rows(repo_workspace: Path) -> None:
    _write(
        repo_workspace / "src/auth/token.py",
        "def issue(value: str) -> str:\n    return value\n",
    )
    _write(
        repo_workspace / "src/api/routes.py",
        "from src.auth import token\n\n"
        "def route() -> str:\n"
        "    return token.issue('x')\n",
    )
    _write(
        repo_workspace / "tests/test_routes.py",
        "from src.api import routes\n\n"
        "def test_route():\n"
        "    assert routes.route() == 'x'\n",
    )
    _write(repo_workspace / "README.md", "# docs\n")

    repo = Repository(
        id=1,
        name="repo",
        clone_url="",
        local_path=repo_workspace.as_posix(),
        status="ready",
    )
    db = _FakeDb(repo)
    git_service = MagicMock()
    git_repo = object()
    git_service.open_repository.return_value = git_repo
    git_service.get_current_sha.return_value = "abc123"
    git_service.list_tracked_files.return_value = [
        "src/auth/token.py",
        "src/api/routes.py",
        "tests/test_routes.py",
        "README.md",
    ]
    git_service.is_binary_file.return_value = False
    git_service.iter_commits.return_value = []

    result = await IndexingService(git_service).index_repository(
        db=db,
        repository_id=1,
        max_commits=0,
    )

    code_files = [item for item in db.added if isinstance(item, CodeFile)]
    symbols = [item for item in db.added if isinstance(item, Symbol)]
    chunks = [item for item in db.added if isinstance(item, CodeChunk)]
    edges = [item for item in db.added if isinstance(item, DependencyEdge)]

    assert result.status == "indexed"
    assert result.files_indexed == 3
    assert result.files_skipped == 1
    assert result.symbols_indexed == 3
    assert result.chunks_indexed == 3
    assert result.dependency_edges_indexed == 2
    assert {item.path for item in code_files} == {
        "src/auth/token.py",
        "src/api/routes.py",
        "tests/test_routes.py",
    }
    assert any(item.is_test for item in code_files)
    assert {item.simple_name for item in symbols} >= {"issue", "route", "test_route"}
    assert all("path:" in item.text for item in chunks)
    assert len(edges) == 2
    assert repo.last_indexed_commit == "abc123"
    assert db.committed is True
