"""
Configuration loading and resolution for GitVane MCP Server.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class Settings:
    """Settings for GitVane MCP Server."""

    server_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    repo: Optional[str] = None
    workspace_dir: Path = Path.cwd()

    def __post_init__(self) -> None:
        # Normalize server_url
        if self.server_url:
            self.server_url = self.server_url.rstrip("/")
        # Normalize workspace_dir
        if isinstance(self.workspace_dir, str):
            self.workspace_dir = Path(self.workspace_dir).resolve()
        else:
            self.workspace_dir = self.workspace_dir.resolve()

    @classmethod
    def find_config_file(cls, start_dir: Optional[Path | str] = None) -> Optional[Path]:
        """Search for .gitvane.json in start_dir and its parent directories."""
        current = Path(start_dir or Path.cwd()).resolve()
        for directory in [current, *current.parents]:
            candidate_1 = directory / ".gitvane.json"
            if candidate_1.is_file():
                return candidate_1
            candidate_2 = directory / ".gitvane" / "config.json"
            if candidate_2.is_file():
                return candidate_2
        return None

    @classmethod
    def load_from_file(cls, file_path: Path) -> dict[str, Any]:
        """Load configuration dictionary from JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    @classmethod
    def load(
        cls,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        repo: Optional[str] = None,
        workspace_dir: Optional[Path | str] = None,
    ) -> Settings:
        """
        Resolve settings with precedence:
        1. Explicit parameters passed to load() (e.g. from CLI options)
        2. Environment variables (GITVANE_SERVER_URL, GITVANE_API_KEY, GITVANE_REPO_ID, GITVANE_WORKSPACE_DIR)
        3. Local config file (.gitvane.json)
        4. Default values
        """
        # Determine base workspace dir
        resolved_ws_dir = (
            Path(workspace_dir).resolve()
            if workspace_dir
            else Path(
                os.environ.get("GITVANE_WORKSPACE_DIR", os.getcwd())
            ).resolve()
        )

        # Attempt to read config file
        file_config: dict[str, Any] = {}
        config_path = cls.find_config_file(resolved_ws_dir)
        if config_path:
            file_config = cls.load_from_file(config_path)

        # Resolve server_url
        final_server_url = (
            server_url
            or os.environ.get("GITVANE_SERVER_URL")
            or file_config.get("server_url")
            or file_config.get("serverUrl")
            or "http://localhost:8000"
        )

        # Resolve api_key
        final_api_key = (
            api_key
            or os.environ.get("GITVANE_API_KEY")
            or os.environ.get("GITVANE_TOKEN")
            or file_config.get("api_key")
            or file_config.get("apiKey")
            or file_config.get("token")
        )

        # Resolve repo
        final_repo = (
            repo
            or os.environ.get("GITVANE_REPO_ID")
            or os.environ.get("GITVANE_REPO")
            or file_config.get("repo_id")
            or file_config.get("repoId")
            or file_config.get("repo")
        )

        return cls(
            server_url=final_server_url,
            api_key=final_api_key,
            repo=final_repo,
            workspace_dir=resolved_ws_dir,
        )
