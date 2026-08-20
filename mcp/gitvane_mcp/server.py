"""
MCP Server factory and registration for GitVane.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from mcp.server import MCPServer
except ImportError:  # pragma: no cover
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        from mcp.server.mcpserver import MCPServer

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings
from gitvane_mcp.tools.impact import handle_analyze_impact
from gitvane_mcp.tools.risk import handle_get_file_risk
from gitvane_mcp.tools.tests import handle_recommend_tests


def create_mcp_server(settings: Optional[Settings] = None) -> MCPServer:
    """Create and configure an MCPServer instance for GitVane."""
    cfg = settings or Settings.load()
    client = GitVaneClient(server_url=cfg.server_url, api_key=cfg.api_key)

    mcp = MCPServer(
        name="gitvane",
        instructions=(
            "GitVane provides architectural impact analysis, test recommendations, "
            "and file risk metrics for code repositories using AST graphs and semantic embeddings."
        ),
    )

    @mcp.tool(
        name="gitvane_analyze_impact",
        description=(
            "Predicts the ripple impact of proposed or uncommitted code changes across the repository "
            "using deterministic AST dependency graphs, historical co-change mining, and semantic embeddings."
        ),
    )
    async def gitvane_analyze_impact(
        changed_files: Optional[list[str]] = None,
        diff: Optional[str] = None,
        top_k: int = 20,
        include_explanation: bool = True,
        max_dependency_depth: int = 3,
        base_ref: Optional[str] = None,
        head_ref: Optional[str] = None,
        repo_id: Optional[str] = None,
    ) -> str:
        """
        Analyze ripple impact of code changes.

        Args:
            changed_files: Optional list of modified file paths.
            diff: Optional raw unified diff string. If both changed_files and diff are omitted,
                  local uncommitted git diff is automatically extracted.
            top_k: Maximum number of impacted files to return (default 20).
            include_explanation: Whether to include LLM summary explanation (default True).
            max_dependency_depth: Maximum graph traversal depth (default 3).
            base_ref: Base git commit SHA / branch reference.
            head_ref: Head git commit SHA / branch reference.
            repo_id: Target repository UUID, name, or clone URL override.
        """
        return await handle_analyze_impact(
            client=client,
            settings=cfg,
            changed_files=changed_files,
            diff=diff,
            top_k=top_k,
            include_explanation=include_explanation,
            max_dependency_depth=max_dependency_depth,
            base_ref=base_ref,
            head_ref=head_ref,
            repo_id=repo_id,
        )

    @mcp.tool(
        name="gitvane_recommend_tests",
        description=(
            "Recommends relevant test files to execute for modified files without having "
            "to run the full test suite."
        ),
    )
    async def gitvane_recommend_tests(
        changed_files: Optional[list[str]] = None,
        impacted_files: Optional[list[str]] = None,
        top_k: int = 10,
        repo_id: Optional[str] = None,
    ) -> str:
        """
        Recommend test files for modified or impacted code.

        Args:
            changed_files: Optional list of modified file paths. Auto-detected if omitted.
            impacted_files: Optional list of upstream impacted file paths.
            top_k: Maximum number of test files to recommend (default 10).
            repo_id: Target repository UUID, name, or clone URL override.
        """
        return await handle_recommend_tests(
            client=client,
            settings=cfg,
            changed_files=changed_files,
            impacted_files=impacted_files,
            top_k=top_k,
            repo_id=repo_id,
        )

    @mcp.tool(
        name="gitvane_get_file_risk",
        description=(
            "Retrieves architectural risk rankings, cyclomatic complexity, churn, "
            "and dependency fan-in scores for files in the repository."
        ),
    )
    async def gitvane_get_file_risk(
        file_path: Optional[str] = None,
        top_k: int = 20,
        language: Optional[str] = None,
        include_tests: bool = False,
        repo_id: Optional[str] = None,
    ) -> str:
        """
        Get risk metrics and architectural hot spots in the codebase.

        Args:
            file_path: Specific file path to query risk score for.
            top_k: Number of highest-risk files to retrieve (default 20).
            language: Filter by programming language (e.g. 'python', 'typescript').
            include_tests: Whether to include test files in risk ranking (default False).
            repo_id: Target repository UUID, name, or clone URL override.
        """
        return await handle_get_file_risk(
            client=client,
            settings=cfg,
            file_path=file_path,
            top_k=top_k,
            language=language,
            include_tests=include_tests,
            repo_id=repo_id,
        )

    return mcp
