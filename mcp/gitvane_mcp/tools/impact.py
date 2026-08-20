"""
Implementation of gitvane_analyze_impact tool handler.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Union

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings
from gitvane_mcp.git_utils import (
    get_changed_files,
    get_working_tree_diff,
    parse_diff_to_changed_files,
)


def normalize_changed_files_input(
    raw_input: Optional[list[Union[str, dict[str, Any]]]]
) -> Optional[list[dict[str, Any]]]:
    """Convert a list of file path strings or partial dicts into ChangedFileInput dicts."""
    if raw_input is None:
        return None

    normalized: list[dict[str, Any]] = []
    for item in raw_input:
        if isinstance(item, str):
            normalized.append({
                "path": item.strip(),
                "change_type": "modified",
                "changed_lines": [],
                "old_path": None,
            })
        elif isinstance(item, dict):
            normalized.append({
                "path": item.get("path", ""),
                "change_type": item.get("change_type", "modified"),
                "changed_lines": item.get("changed_lines", []),
                "old_path": item.get("old_path"),
            })
    return normalized


async def handle_analyze_impact(
    client: GitVaneClient,
    settings: Settings,
    changed_files: Optional[list[Union[str, dict[str, Any]]]] = None,
    diff: Optional[str] = None,
    top_k: int = 20,
    include_explanation: bool = True,
    max_dependency_depth: int = 3,
    base_ref: Optional[str] = None,
    head_ref: Optional[str] = None,
    repo_id: Optional[str] = None,
) -> str:
    """
    Handle the gitvane_analyze_impact tool call.
    Resolves repository, collects local uncommitted diff/changes if needed,
    calls backend API, and returns formatted JSON result.
    """
    # 1. Resolve repository UUID
    repository_id = await client.resolve_repository(
        repo_hint=repo_id or settings.repo,
        workspace_dir=settings.workspace_dir,
    )

    # 2. Normalize or auto-extract changed files / diff
    norm_changed_files = normalize_changed_files_input(changed_files)
    effective_diff = diff

    if not norm_changed_files and not effective_diff:
        # Auto-extract from local git repository
        local_diff = get_working_tree_diff(settings.workspace_dir)
        if local_diff and local_diff.strip():
            effective_diff = local_diff
            norm_changed_files = parse_diff_to_changed_files(local_diff)
        else:
            # Fallback to untracked/status if no diff
            norm_changed_files = get_changed_files(settings.workspace_dir)

    # 3. Call backend API
    result = await client.analyze_impact(
        repository_id=repository_id,
        changed_files=norm_changed_files,
        raw_diff=effective_diff,
        base_ref=base_ref,
        head_ref=head_ref,
        top_k=top_k,
        include_explanation=include_explanation,
        max_dependency_depth=max_dependency_depth,
    )

    return json.dumps(result, indent=2)
