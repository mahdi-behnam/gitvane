from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

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


def test_run_evaluation_endpoint_success() -> None:
    mock_svc = MagicMock()
    mock_svc.run_evaluation = AsyncMock(
        return_value=EvaluationRunResponse(
            evaluation_run_id=1,
            status="completed",
            summary={"evaluated_commits": 2},
        )
    )

    app.dependency_overrides[get_db] = _noop_db
    app.dependency_overrides[get_evaluation_service] = lambda: mock_svc
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/evaluation/run",
            json={"repository_id": 1, "methods": ["hybrid"], "k_values": [5]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["evaluation_run_id"] == 1
    mock_svc.run_evaluation.assert_awaited_once()


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
