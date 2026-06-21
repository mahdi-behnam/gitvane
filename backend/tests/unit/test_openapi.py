from fastapi.testclient import TestClient

from app.main import app


def test_openapi_includes_documented_api_groups() -> None:
    client = TestClient(app)

    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    expected_paths = {
        "/api/v1/health",
        "/api/v1/repositories",
        "/api/v1/repositories/{repository_id}",
        "/api/v1/repositories/{repository_id}/index",
        "/api/v1/repositories/{repository_id}/index/status",
        "/api/v1/search/semantic",
        "/api/v1/impact/analyze",
        "/api/v1/impact/runs/{analysis_run_id}",
        "/api/v1/tests/recommend",
        "/api/v1/risk/repositories/{repository_id}/files",
        "/api/v1/evaluation/run",
        "/api/v1/evaluation/{evaluation_run_id}",
        "/api/v1/evaluation/{evaluation_run_id}/report",
        "/api/v1/graph/repositories/{repository_id}/file/{file_id}/neighbors",
        "/api/v1/graph/repositories/{repository_id}/subgraph",
    }

    assert expected_paths <= set(paths)
