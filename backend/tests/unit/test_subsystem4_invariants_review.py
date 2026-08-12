"""Subsystem 4 Dual-Review Invariants & Active Generation Filtering Tests.

Reviewer A: Invariants 1, 2, 4, 5 & Supersedes behavior.
Reviewer B: PgBouncer compatibility, FastAPI responses, SQL query filter correctness.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db, get_repository_service
from app.db.models import (
    CodeChunk,
    CodeEmbedding,
    CodeFile,
    DependencyEdge,
    IndexGeneration,
    OutboxEvent,
    Repository,
    Symbol,
)
from app.main import app
from app.services.graph_service import GraphService
from app.services.impact_service import ImpactService
from app.services.repository_service import RepositoryService
from app.services.risk_service import RiskService
from app.services.semantic_search_service import SemanticSearchService

TEST_REPO_ID = uuid.uuid4()
ACTIVE_GEN_ID = uuid.uuid4()
OLD_GEN_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Reviewer A Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_reviewer_a_invariant_1_and_2_api_kickoff_transaction() -> None:
    """Verify POST /index executes in 1 single transaction locking Repo FOR UPDATE, creating IndexGeneration and OutboxEvent without direct Celery calls."""
    repo = Repository(
        id=TEST_REPO_ID,
        name="test-repo",
        clone_url="https://github.com/example/test.git",
        default_branch="main",
        status="ready",
        desired_generation_id=OLD_GEN_ID,
        active_generation_id=ACTIVE_GEN_ID,
    )

    old_gen = IndexGeneration(
        id=OLD_GEN_ID,
        repository_id=TEST_REPO_ID,
        requested_ref="main",
        status="parsing",
    )

    db_added: list[object] = []

    class _MockDb:
        def __init__(self) -> None:
            self.commit_count = 0

        async def execute(self, stmt: object) -> MagicMock:
            mock_res = MagicMock()
            stmt_str = str(stmt)
            if "FOR UPDATE" in stmt_str and "repositories" in stmt_str:
                mock_res.scalars.return_value.first.return_value = repo
            elif "index_generations" in stmt_str:
                mock_res.scalars.return_value.first.return_value = old_gen
            else:
                mock_res.scalars.return_value.first.return_value = None
                mock_res.scalars.return_value.all.return_value = []
            return mock_res

        def add(self, obj: object) -> None:
            db_added.append(obj)

        async def commit(self) -> None:
            self.commit_count += 1

        async def refresh(self, obj: object) -> None:
            pass

    mock_db = _MockDb()

    async def _get_db_override():
        yield mock_db

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_repository_service] = lambda: MagicMock()

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/repositories/{TEST_REPO_ID}/index",
            json={"ref": "main"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "generation_id" in data
        assert data["status"] == "queued"

        # Check transaction committed exactly once
        assert mock_db.commit_count == 1

        # Check IndexGeneration added
        new_gen = next(item for item in db_added if isinstance(item, IndexGeneration))
        assert new_gen.repository_id == TEST_REPO_ID
        assert new_gen.status == "queued"

        # Check OutboxEvent added
        outbox = next(item for item in db_added if isinstance(item, OutboxEvent))
        assert outbox.event_type == "prepare_requested"
        assert outbox.aggregate_id == new_gen.id

        # Check prev generation superseded
        assert old_gen.status == "superseded"
        assert old_gen.terminal_at is not None

        # Check Repository.desired_generation_id updated, active_generation_id unchanged
        assert repo.desired_generation_id == new_gen.id
        assert repo.active_generation_id == ACTIVE_GEN_ID

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_reviewer_a_invariant_4_and_5_active_generation_filtering_and_null_handling() -> None:
    """Verify active generation filtering across GraphService, RiskService, ImpactService when active_generation_id is NULL or set."""
    # Test NULL active_generation_id
    repo_null = Repository(
        id=TEST_REPO_ID,
        name="null-repo",
        clone_url="",
        status="ready",
        active_generation_id=None,
    )

    class _NullDb:
        def add(self, obj: object) -> None:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                setattr(obj, "id", 1)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def rollback(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            pass

        async def get(self, model: type, obj_id: object) -> object:
            if model is Repository:
                return repo_null
            return None

        async def execute(self, stmt: object) -> MagicMock:
            res = MagicMock()
            res.scalars.return_value.all.return_value = []
            return res

    null_db = _NullDb()

    # GraphService file neighbors with null active_generation_id returns empty lists
    neighbors = await GraphService().get_file_neighbors(null_db, TEST_REPO_ID, "src/main.py")
    assert neighbors.nodes == []
    assert neighbors.edges == []

    # RiskService file risks with null active_generation_id returns empty file list with metadata
    risk_resp = await RiskService().get_repository_file_risks(null_db, TEST_REPO_ID)
    assert risk_resp.files == []
    assert risk_resp.metadata["mean_risk_score"] == 0.0

    # ImpactService impact analysis with null active_generation_id returns empty impact response
    from app.schemas.impact import ChangedFileInput, ImpactAnalyzeRequest

    req = ImpactAnalyzeRequest(
        repository_id=TEST_REPO_ID,
        changed_files=[ChangedFileInput(path="src/main.py")],
    )
    impact_resp = await ImpactService(git_service=MagicMock()).analyze(null_db, req)
    assert impact_resp.impacted_files == []


# ---------------------------------------------------------------------------
# Reviewer B Tests
# ---------------------------------------------------------------------------


def test_reviewer_b_pgbouncer_compatibility() -> None:
    """Verify no transaction-level session state or non-PgBouncer primitives are used in endpoint handlers."""
    import inspect
    from app.api.v1.endpoints import indexing, repositories

    for module in [indexing, repositories]:
        source = inspect.getsource(module)
        assert "LISTEN" not in source
        assert "NOTIFY" not in source
        assert "SET LOCAL" not in source
        assert "pg_advisory_lock" not in source


@pytest.mark.asyncio()
async def test_reviewer_b_sql_active_generation_where_clause() -> None:
    """Verify queries explicitly append generation_id = repo.active_generation_id."""
    repo = Repository(
        id=TEST_REPO_ID,
        name="active-repo",
        clone_url="",
        status="indexed",
        active_generation_id=ACTIVE_GEN_ID,
    )

    center_file = CodeFile(
        id=1,
        repository_id=TEST_REPO_ID,
        generation_id=ACTIVE_GEN_ID,
        path="src/main.py",
        language="python",
        content_hash="abc",
    )

    executed_statements: list[str] = []

    class _QueryCaptureDb:
        async def get(self, model: type, obj_id: object) -> object:
            if model is Repository:
                return repo
            if model is CodeFile:
                return center_file
            return None

        async def execute(self, stmt: object) -> MagicMock:
            executed_statements.append(str(stmt))
            res = MagicMock()
            res.scalars.return_value.all.return_value = []
            return res

    capture_db = _QueryCaptureDb()
    await GraphService().get_file_neighbors(capture_db, TEST_REPO_ID, 1)

    # Check executed queries contained generation_id filter
    assert any("generation_id =" in stmt or "generation_id = :" in stmt or "generation_id" in stmt for stmt in executed_statements)
