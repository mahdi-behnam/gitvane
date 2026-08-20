"""
Unit tests for MCP tool handlers (impact, tests, risk).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import respx
from httpx import Response

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings
from gitvane_mcp.server import create_mcp_server
from gitvane_mcp.tools.impact import handle_analyze_impact
from gitvane_mcp.tools.risk import handle_get_file_risk
from gitvane_mcp.tools.tests import handle_recommend_tests


@respx.mock
async def test_tool_analyze_impact_explicit_args(
    mock_client: GitVaneClient, mock_settings: Settings
) -> None:
    repo_id = mock_settings.repo
    respx.post("http://mock-gitvane:8000/api/v1/impact/analyze").mock(
        return_value=Response(
            200,
            json={
                "analysis_run_id": 101,
                "repository_id": repo_id,
                "impacted_files": [{"rank": 1, "path": "services/auth.py", "score": 0.92}],
                "recommended_tests": [{"path": "tests/test_auth.py", "score": 0.95}],
            },
        )
    )

    output = await handle_analyze_impact(
        client=mock_client,
        settings=mock_settings,
        changed_files=["services/user.py", {"path": "services/base.py", "change_type": "modified"}],
        top_k=10,
    )

    parsed = json.loads(output)
    assert parsed["analysis_run_id"] == 101
    assert parsed["impacted_files"][0]["path"] == "services/auth.py"


@respx.mock
async def test_tool_analyze_impact_auto_diff(
    mock_client: GitVaneClient, temp_git_repo: Path
) -> None:
    repo_id = "7b886d91-3839-4458-9a3b-2856f616d24f"
    settings = Settings(
        server_url="http://mock-gitvane:8000",
        api_key="test-key",
        repo=repo_id,
        workspace_dir=temp_git_repo,
    )

    # Modify a file in temp_git_repo
    (temp_git_repo / "main.py").write_text("def hello():\n    return 'changed'\n")

    respx.post("http://mock-gitvane:8000/api/v1/impact/analyze").mock(
        return_value=Response(
            200,
            json={
                "analysis_run_id": 102,
                "repository_id": repo_id,
                "impacted_files": [],
                "recommended_tests": [],
            },
        )
    )

    output = await handle_analyze_impact(
        client=mock_client,
        settings=settings,
    )
    parsed = json.loads(output)
    assert parsed["analysis_run_id"] == 102


@respx.mock
async def test_tool_recommend_tests(
    mock_client: GitVaneClient, mock_settings: Settings
) -> None:
    repo_id = mock_settings.repo
    respx.post("http://mock-gitvane:8000/api/v1/tests/recommend").mock(
        return_value=Response(
            200,
            json={
                "repository_id": repo_id,
                "recommended_tests": [{"path": "tests/test_model.py", "score": 0.89}],
            },
        )
    )

    output = await handle_recommend_tests(
        client=mock_client,
        settings=mock_settings,
        changed_files=["models/user.py"],
        top_k=5,
    )

    parsed = json.loads(output)
    assert len(parsed["recommended_tests"]) == 1
    assert parsed["recommended_tests"][0]["path"] == "tests/test_model.py"


@respx.mock
async def test_tool_get_file_risk(
    mock_client: GitVaneClient, mock_settings: Settings
) -> None:
    repo_id = mock_settings.repo
    respx.get(f"http://mock-gitvane:8000/api/v1/risk/repositories/{repo_id}/files").mock(
        return_value=Response(
            200,
            json={
                "repository_id": repo_id,
                "files": [{"path": "core/router.py", "risk_score": 0.77}],
            },
        )
    )

    output = await handle_get_file_risk(
        client=mock_client,
        settings=mock_settings,
        file_path="core/router.py",
    )

    parsed = json.loads(output)
    assert len(parsed["files"]) == 1
    assert parsed["files"][0]["path"] == "core/router.py"


@respx.mock
async def test_server_tools_integration(mock_settings: Settings) -> None:
    repo_id = mock_settings.repo
    respx.post("http://mock-gitvane:8000/api/v1/impact/analyze").mock(
        return_value=Response(200, json={"analysis_run_id": 200, "repository_id": repo_id, "impacted_files": []})
    )
    respx.post("http://mock-gitvane:8000/api/v1/tests/recommend").mock(
        return_value=Response(200, json={"repository_id": repo_id, "recommended_tests": []})
    )
    respx.get(f"http://mock-gitvane:8000/api/v1/risk/repositories/{repo_id}/files").mock(
        return_value=Response(200, json={"repository_id": repo_id, "files": []})
    )

    server = create_mcp_server(mock_settings)

    # Test calling tools via server tool handlers
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "gitvane_analyze_impact" in tool_names
    assert "gitvane_recommend_tests" in tool_names
    assert "gitvane_get_file_risk" in tool_names

    # Call tools through server.call_tool
    impact_res = await server.call_tool("gitvane_analyze_impact", {"changed_files": ["foo.py"]})
    assert impact_res is not None

    test_res = await server.call_tool("gitvane_recommend_tests", {"changed_files": ["foo.py"]})
    assert test_res is not None

    risk_res = await server.call_tool("gitvane_get_file_risk", {"file_path": "foo.py"})
    assert risk_res is not None
