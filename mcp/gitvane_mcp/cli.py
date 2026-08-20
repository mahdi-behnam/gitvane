"""
Command-line interface entry point for GitVane MCP server.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from gitvane_mcp import __version__
from gitvane_mcp.config import Settings
from gitvane_mcp.server import create_mcp_server


@click.command(name="gitvane-mcp")
@click.version_option(version=__version__, prog_name="gitvane-mcp")
@click.option(
    "--server-url",
    envvar="GITVANE_SERVER_URL",
    default=None,
    help="GitVane backend REST API base URL (default: http://localhost:8000).",
)
@click.option(
    "--api-key",
    envvar="GITVANE_API_KEY",
    default=None,
    help="GitVane API authentication key or Personal Access Token.",
)
@click.option(
    "--repo",
    envvar="GITVANE_REPO_ID",
    default=None,
    help="Repository UUID, name, or clone URL to bind to.",
)
@click.option(
    "--workspace-dir",
    envvar="GITVANE_WORKSPACE_DIR",
    default=None,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to local repository workspace (default: current directory).",
)
@click.option(
    "--transport",
    default="stdio",
    type=click.Choice(["stdio", "sse"], case_sensitive=False),
    help="MCP transport protocol (default: stdio).",
)
def main(
    server_url: Optional[str],
    api_key: Optional[str],
    repo: Optional[str],
    workspace_dir: Optional[Path],
    transport: str,
) -> None:
    """
    GitVane Model Context Protocol (MCP) server.

    Connects AI coding assistants (Claude Desktop, Cursor, Claude Code, Windsurf, Antigravity)
    to GitVane's AST dependency graph, impact prediction, and test recommendation engine.
    """
    settings = Settings.load(
        server_url=server_url,
        api_key=api_key,
        repo=repo,
        workspace_dir=workspace_dir,
    )

    server = create_mcp_server(settings)

    if transport.lower() == "stdio":
        server.run(transport="stdio")
    elif transport.lower() == "sse":
        server.run(transport="sse")
    else:
        click.echo(f"Unsupported transport: {transport}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
