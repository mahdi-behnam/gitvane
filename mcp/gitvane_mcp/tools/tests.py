"""
Implementation of gitvane_recommend_tests tool handler.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Union

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings
from gitvane_mcp.git_utils import get_changed_files
from gitvane_mcp.tools.impact import normalize_changed_files_input


async def handle_recommend_tests(
    client: GitVaneClient,
    settings: Settings,
    changed_files: Optional[list[Union[str, dict[str, Any]]]] = None,
    impacted_files: Optional[list[str]] = None,
    top_k: int = 10,
    repo_id: Optional[str] = None,
) -> str:
    """
    Handle the gitvane_recommend_tests tool call.
    Resolves repository, identifies changed files if omitted, calls backend API,
    and returns formatted JSON response.
    """
    # 1. Resolve repository UUID
    repository_id = await client.resolve_repository(
        repo_hint=repo_id or settings.repo,
        workspace_dir=settings.workspace_dir,
    )

    # 2. Normalize or auto-extract changed files
    norm_changed_files = normalize_changed_files_input(changed_files)
    if not norm_changed_files:
        norm_changed_files = get_changed_files(settings.workspace_dir)

    # 3. Call backend API
    result = await client.recommend_tests(
        repository_id=repository_id,
        changed_files=norm_changed_files,
        impacted_files=impacted_files or [],
        top_k=top_k,
    )

    return json.dumps(result, indent=2)
