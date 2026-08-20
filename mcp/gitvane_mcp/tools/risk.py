"""
Implementation of gitvane_get_file_risk tool handler.
"""

from __future__ import annotations

import json
from typing import Optional

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings


async def handle_get_file_risk(
    client: GitVaneClient,
    settings: Settings,
    file_path: Optional[str] = None,
    top_k: int = 20,
    language: Optional[str] = None,
    include_tests: bool = False,
    repo_id: Optional[str] = None,
) -> str:
    """
    Handle the gitvane_get_file_risk tool call.
    Retrieves architectural risk rankings, cyclomatic complexity, churn,
    and dependency fan-in scores for files in the repository.
    """
    # 1. Resolve repository UUID
    repository_id = await client.resolve_repository(
        repo_hint=repo_id or settings.repo,
        workspace_dir=settings.workspace_dir,
    )

    # 2. Call backend API
    result = await client.get_file_risk(
        repository_id=repository_id,
        file_path=file_path,
        top_k=top_k,
        language=language,
        include_tests=include_tests,
    )

    return json.dumps(result, indent=2)
