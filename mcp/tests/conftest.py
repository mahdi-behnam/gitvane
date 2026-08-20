"""
Pytest fixtures and helpers for gitvane-mcp tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Generator
import pytest

from gitvane_mcp.client import GitVaneClient
from gitvane_mcp.config import Settings


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """Fixture providing isolated Settings."""
    return Settings(
        server_url="http://mock-gitvane:8000",
        api_key="test-api-key-12345",
        repo="7b886d91-3839-4458-9a3b-2856f616d24f",
        workspace_dir=tmp_path,
    )


@pytest.fixture
def mock_client() -> GitVaneClient:
    """Fixture providing GitVaneClient pointing to mock server."""
    return GitVaneClient(
        server_url="http://mock-gitvane:8000",
        api_key="test-api-key-12345",
    )


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with initial commit and tracked files."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/org/test_repo.git"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    # Add initial file
    initial_file = repo_dir / "main.py"
    initial_file.write_text("def hello():\n    return 'hello world'\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True, check=True)

    yield repo_dir
