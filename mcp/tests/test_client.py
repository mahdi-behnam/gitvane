"""
Unit tests for GitVaneClient async HTTP client and repository resolution.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
import respx
from httpx import Response

from gitvane_mcp.client import GitVaneAPIError, GitVaneClient


@respx.mock
async def test_get_repositories(mock_client: GitVaneClient) -> None:
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "7b886d91-3839-4458-9a3b-2856f616d24f",
                        "name": "test_repo",
                        "clone_url": "https://github.com/org/test_repo.git",
                    }
                ],
                "total": 1,
            },
        )
    )

    data = await mock_client.get_repositories()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "test_repo"


@respx.mock
async def test_resolve_repository_by_uuid(mock_client: GitVaneClient) -> None:
    target_uuid = "7b886d91-3839-4458-9a3b-2856f616d24f"
    resolved = await mock_client.resolve_repository(repo_hint=target_uuid)
    assert resolved == target_uuid


@respx.mock
async def test_resolve_repository_by_name(mock_client: GitVaneClient) -> None:
    target_uuid = "7b886d91-3839-4458-9a3b-2856f616d24f"
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": target_uuid,
                        "name": "my-service",
                        "clone_url": "https://github.com/org/my-service.git",
                    },
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "other-service",
                        "clone_url": "https://github.com/org/other-service.git",
                    },
                ],
                "total": 2,
            },
        )
    )

    resolved = await mock_client.resolve_repository(repo_hint="my-service")
    assert resolved == target_uuid


@respx.mock
async def test_resolve_repository_from_git_remote(
    mock_client: GitVaneClient, temp_git_repo: Path
) -> None:
    target_uuid = "7b886d91-3839-4458-9a3b-2856f616d24f"
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": target_uuid,
                        "name": "test_repo",
                        "clone_url": "https://github.com/org/test_repo.git",
                    }
                ],
                "total": 1,
            },
        )
    )

    resolved = await mock_client.resolve_repository(workspace_dir=temp_git_repo)
    assert resolved == target_uuid


@respx.mock
async def test_resolve_repository_ambiguity_error(mock_client: GitVaneClient) -> None:
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "repo-alpha",
                        "clone_url": "https://github.com/org/alpha.git",
                    },
                    {
                        "id": "22222222-2222-2222-2222-222222222222",
                        "name": "repo-beta",
                        "clone_url": "https://github.com/org/beta.git",
                    },
                ],
                "total": 2,
            },
        )
    )

    with pytest.raises(GitVaneAPIError) as excinfo:
        await mock_client.resolve_repository(repo_hint="non-existent")
    assert "Could not automatically resolve repository" in str(excinfo.value)


@respx.mock
async def test_resolve_repository_empty_list_error(mock_client: GitVaneClient) -> None:
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(200, json={"items": [], "total": 0})
    )

    with pytest.raises(GitVaneAPIError) as excinfo:
        await mock_client.resolve_repository()
    assert "No repositories found on GitVane server" in str(excinfo.value)


@respx.mock
async def test_analyze_impact(mock_client: GitVaneClient) -> None:
    repo_id = "7b886d91-3839-4458-9a3b-2856f616d24f"
    expected_response = {
        "analysis_run_id": 42,
        "repository_id": repo_id,
        "changed_files": [{"path": "app/main.py", "change_type": "modified", "changed_lines": []}],
        "changed_symbols": [],
        "impacted_files": [
            {
                "rank": 1,
                "path": "app/service.py",
                "score": 0.88,
                "component_scores": {"ast_coupling": 0.9},
                "reasons": [{"type": "ast_import", "message": "Direct import", "confidence": 0.95}],
                "recommended_tests": [],
            }
        ],
        "recommended_tests": [{"path": "tests/test_service.py", "score": 0.9}],
        "risk_summary": {"highest_risk_files": []},
        "llm_explanation": "Changes in app/main.py impact app/service.py.",
    }

    respx.post("http://mock-gitvane:8000/api/v1/impact/analyze").mock(
        return_value=Response(200, json=expected_response)
    )

    result = await mock_client.analyze_impact(
        repository_id=repo_id,
        changed_files=[{"path": "app/main.py", "change_type": "modified", "changed_lines": []}],
        raw_diff="diff --git a/app/main.py b/app/main.py",
        base_ref="main",
        head_ref="feature",
        top_k=5,
    )
    assert result["analysis_run_id"] == 42
    assert len(result["impacted_files"]) == 1
    assert result["impacted_files"][0]["path"] == "app/service.py"


@respx.mock
async def test_recommend_tests(mock_client: GitVaneClient) -> None:
    repo_id = "7b886d91-3839-4458-9a3b-2856f616d24f"
    expected_response = {
        "repository_id": repo_id,
        "changed_files": [{"path": "app/main.py", "change_type": "modified", "changed_lines": []}],
        "recommended_tests": [
            {
                "path": "tests/test_main.py",
                "score": 0.95,
                "reason": "Direct test file match",
                "linked_files": ["app/main.py"],
            }
        ],
    }

    respx.post("http://mock-gitvane:8000/api/v1/tests/recommend").mock(
        return_value=Response(200, json=expected_response)
    )

    result = await mock_client.recommend_tests(
        repository_id=repo_id,
        changed_files=[{"path": "app/main.py", "change_type": "modified", "changed_lines": []}],
        top_k=5,
    )
    assert len(result["recommended_tests"]) == 1
    assert result["recommended_tests"][0]["path"] == "tests/test_main.py"


@respx.mock
async def test_get_file_risk(mock_client: GitVaneClient) -> None:
    repo_id = "7b886d91-3839-4458-9a3b-2856f616d24f"
    expected_response = {
        "repository_id": repo_id,
        "files": [
            {
                "path": "app/core/engine.py",
                "risk_score": 0.85,
                "components": {"fan_in": 12.0, "churn": 25.0},
                "reasons": ["High cyclomatic complexity", "Frequently co-changed"],
            }
        ],
        "metadata": {"total_files_analyzed": 150},
    }

    respx.get(f"http://mock-gitvane:8000/api/v1/risk/repositories/{repo_id}/files").mock(
        return_value=Response(200, json=expected_response)
    )

    result = await mock_client.get_file_risk(
        repository_id=repo_id, file_path="app/core/engine.py", language="python", top_k=10
    )
    assert len(result["files"]) == 1
    assert result["files"][0]["path"] == "app/core/engine.py"


@respx.mock
async def test_client_error_responses(mock_client: GitVaneClient) -> None:
    # 401
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(401, json={"detail": "Invalid credentials"})
    )
    with pytest.raises(GitVaneAPIError) as exc401:
        await mock_client.get_repositories()
    assert exc401.value.status_code == 401

    # 404
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(GitVaneAPIError) as exc404:
        await mock_client.get_repositories()
    assert exc404.value.status_code == 404

    # 422
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(422, json={"detail": "Invalid input schema"})
    )
    with pytest.raises(GitVaneAPIError) as exc422:
        await mock_client.get_repositories()
    assert exc422.value.status_code == 422

    # 500
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        return_value=Response(500, text="Internal server error")
    )
    with pytest.raises(GitVaneAPIError) as exc500:
        await mock_client.get_repositories()
    assert exc500.value.status_code == 500


@respx.mock
async def test_client_network_errors(mock_client: GitVaneClient) -> None:
    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    with pytest.raises(GitVaneAPIError) as exc_conn:
        await mock_client.get_repositories()
    assert "Could not connect to GitVane server" in str(exc_conn.value)

    respx.get("http://mock-gitvane:8000/api/v1/repositories").mock(
        side_effect=httpx.TimeoutException("Timeout")
    )
    with pytest.raises(GitVaneAPIError) as exc_time:
        await mock_client.get_repositories()
    assert "timed out" in str(exc_time.value)
