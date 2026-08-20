"""
Unit tests for configuration loading and resolution.
"""

from __future__ import annotations

import json
from pathlib import Path

from gitvane_mcp.config import Settings


def test_settings_defaults(monkeypatch, tmp_path: Path) -> None:
    # Clear env vars
    monkeypatch.delenv("GITVANE_SERVER_URL", raising=False)
    monkeypatch.delenv("GITVANE_API_KEY", raising=False)
    monkeypatch.delenv("GITVANE_TOKEN", raising=False)
    monkeypatch.delenv("GITVANE_REPO_ID", raising=False)
    monkeypatch.delenv("GITVANE_REPO", raising=False)

    settings = Settings.load(workspace_dir=tmp_path)
    assert settings.server_url == "http://localhost:8000"
    assert settings.api_key is None
    assert settings.repo is None
    assert settings.workspace_dir == tmp_path.resolve()


def test_settings_trailing_slash_stripped() -> None:
    settings = Settings(server_url="http://localhost:8000///")
    assert settings.server_url == "http://localhost:8000"


def test_settings_from_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITVANE_SERVER_URL", "https://api.gitvane.internal")
    monkeypatch.setenv("GITVANE_API_KEY", "env-secret-key")
    monkeypatch.setenv("GITVANE_REPO_ID", "12345678-1234-5678-1234-567812345678")

    settings = Settings.load(workspace_dir=tmp_path)
    assert settings.server_url == "https://api.gitvane.internal"
    assert settings.api_key == "env-secret-key"
    assert settings.repo == "12345678-1234-5678-1234-567812345678"


def test_settings_from_json_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITVANE_SERVER_URL", raising=False)
    monkeypatch.delenv("GITVANE_API_KEY", raising=False)
    monkeypatch.delenv("GITVANE_REPO_ID", raising=False)

    config_file = tmp_path / ".gitvane.json"
    config_file.write_text(
        json.dumps({
            "server_url": "https://gitvane.company.com",
            "api_key": "file-token-123",
            "repo_id": "99999999-9999-9999-9999-999999999999",
        }),
        encoding="utf-8",
    )

    settings = Settings.load(workspace_dir=tmp_path)
    assert settings.server_url == "https://gitvane.company.com"
    assert settings.api_key == "file-token-123"
    assert settings.repo == "99999999-9999-9999-9999-999999999999"


def test_settings_cli_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GITVANE_SERVER_URL", "https://env-url.com")
    monkeypatch.setenv("GITVANE_API_KEY", "env-key")

    settings = Settings.load(
        server_url="https://cli-override.com",
        api_key="cli-key",
        repo="my-custom-repo",
        workspace_dir=tmp_path,
    )
    assert settings.server_url == "https://cli-override.com"
    assert settings.api_key == "cli-key"
    assert settings.repo == "my-custom-repo"
