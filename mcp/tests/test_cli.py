"""
Unit tests for CLI interface and server initialization.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from gitvane_mcp import __version__
from gitvane_mcp.cli import main
from gitvane_mcp.config import Settings
from gitvane_mcp.server import create_mcp_server


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "GitVane Model Context Protocol (MCP) server" in result.output
    assert "--server-url" in result.output
    assert "--api-key" in result.output
    assert "--repo" in result.output


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_create_mcp_server_tools_registered() -> None:
    settings = Settings(
        server_url="http://mock-server:8000",
        api_key="test-key",
        repo="7b886d91-3839-4458-9a3b-2856f616d24f",
    )
    server = create_mcp_server(settings)
    assert server.name == "gitvane"
    assert hasattr(server, "run")


@patch("gitvane_mcp.cli.create_mcp_server")
def test_cli_run_stdio(mock_create_server: MagicMock) -> None:
    mock_server_inst = MagicMock()
    mock_create_server.return_value = mock_server_inst

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--server-url", "http://localhost:9000", "--api-key", "my-key", "--transport", "stdio"],
    )
    assert result.exit_code == 0
    mock_server_inst.run.assert_called_once_with(transport="stdio")


@patch("gitvane_mcp.cli.create_mcp_server")
def test_cli_run_sse(mock_create_server: MagicMock) -> None:
    mock_server_inst = MagicMock()
    mock_create_server.return_value = mock_server_inst

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--transport", "sse"],
    )
    assert result.exit_code == 0
    mock_server_inst.run.assert_called_once_with(transport="sse")
