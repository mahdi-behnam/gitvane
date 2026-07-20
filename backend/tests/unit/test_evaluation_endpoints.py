from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_evaluation_service
from app.core.errors import RepositoryNotFoundError
from app.main import app
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)


async def _noop_db() -> AsyncGenerator[Any, None]:
    yield MagicMock()


@patch("app.api.v1.endpoints.evaluation.SessionLocal")
@patch("app.api.v1.endpoints.evaluation.EvaluationService")
def test_run_evaluation_endpoint_success(
    mock_evaluation_service_cls: MagicMock, mock_session_local_cls: MagicMock
) -> None:
    mock_db = MagicMock()
    mock_repo = MagicMock()
    mock_repo.id = 1
    mock_db.get = AsyncMock(return_value=mock_repo)
    mock_db.commit = AsyncMock()

    async def mock_refresh(run):
        run.id = 1

    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    async def mock_get_db() -> AsyncGenerator[Any, None]:
        yield mock_db

    app.dependency_overrides[get_db] = mock_get_db

    mock_async_db = MagicMock()
    mock_session_local_cls.return_value.__aenter__.return_value = mock_async_db

    mock_svc_instance = mock_evaluation_service_cls.return_value
    mock_svc_instance.execute_evaluation = AsyncMock()

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/evaluation/run",
            json={"repository_id": 1, "methods": ["hybrid"], "k_values": [5]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["evaluation_run_id"] == 1
    assert response.json()["status"] == "running"

    mock_db.commit.assert_awaited_once()
    mock_session_local_cls.assert_called_once()
    mock_svc_instance.execute_evaluation.assert_awaited_once_with(
        db=mock_async_db,
        evaluation_run_id=1,
        commit_limit=100,
        methods=["hybrid"],
        k_values=[5],
    )


def test_get_evaluation_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_evaluation = AsyncMock(
        return_value=EvaluationStatusResponse(
            evaluation_run_id=1,
            repository_id=1,
            name="Eval",
            status="completed",
            methods=["hybrid"],
            commit_limit=100,
            summary={},
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_evaluation_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/evaluation/1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_get_evaluation_report_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.get_report = AsyncMock(
        return_value=EvaluationReportResponse(
            evaluation_run_id=1,
            markdown="# Evaluation Report",
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_evaluation_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/evaluation/1/report")
        markdown_response = client.get("/api/v1/evaluation/1/report.md")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["markdown"] == "# Evaluation Report"
    assert markdown_response.status_code == 200
    assert markdown_response.text == "# Evaluation Report"


def test_evaluation_endpoint_not_found() -> None:
    mock_svc = MagicMock()
    mock_svc.get_evaluation = AsyncMock(
        side_effect=RepositoryNotFoundError("Evaluation run with id=99 does not exist")
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_evaluation_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.get("/api/v1/evaluation/99")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
