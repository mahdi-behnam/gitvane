# GitVane MCP Server (`gitvane-mcp`)

Model Context Protocol (MCP) server for **GitVane**, providing AI coding assistants (Claude Desktop, Cursor, Claude Code, Windsurf, OpenAI Codex, and Antigravity) with deep architectural impact analysis, test recommendation, and file risk intelligence.

---

## Features

- **`gitvane_analyze_impact`**: Predicts the ripple impact of proposed or uncommitted code changes across the repository using deterministic AST dependency graphs, historical co-change mining, and semantic embeddings. Auto-extracts local git working copy diffs if not explicitly passed.
- **`gitvane_recommend_tests`**: Recommends targeted test files to execute for modified files without having to run the full test suite.
- **`gitvane_get_file_risk`**: Retrieves architectural risk rankings, cyclomatic complexity, churn, and dependency fan-in scores for files in the repository.

---

## Installation

### Via `uvx` (Recommended - Zero Installation)

```bash
uvx gitvane-mcp --help
```

### Via `pip`

```bash
pip install gitvane-mcp
```

### Development Mode

```bash
cd mcp
pip install -e .
```

---

## Configuration & Resolution

`gitvane-mcp` resolves settings using the following precedence:
1. **CLI Options**: `--server-url`, `--api-key`, `--repo`, `--workspace-dir`
2. **Environment Variables**: `GITVANE_SERVER_URL`, `GITVANE_API_KEY`, `GITVANE_REPO_ID`, `GITVANE_WORKSPACE_DIR`
3. **Workspace Config File**: `.gitvane.json` in the workspace root or parent directories.
4. **Auto-Detection**: Local Git remote origin URL (`git remote get-url origin`) matching indexed repositories on the GitVane server.

### Local Workspace Configuration (`.gitvane.json`)

You can drop a `.gitvane.json` file in your repository root:

```json
{
  "server_url": "http://localhost:8000",
  "api_key": "your-personal-api-key",
  "repo_id": "7b886d91-3839-4458-9a3b-2856f616d24f"
}
```

---

## Client Integration Configurations

### 1. Antigravity Configuration

Add to your `mcp_servers` configuration or `.gemini/antigravity/mcp/gitvane/` directory:

```json
{
  "mcpServers": {
    "gitvane": {
      "command": "uvx",
      "args": [
        "gitvane-mcp",
        "--server-url", "http://localhost:8000"
      ],
      "env": {
        "GITVANE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

### 2. Claude Desktop

Add to `claude_desktop_config.json`:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gitvane": {
      "command": "uvx",
      "args": [
        "gitvane-mcp",
        "--server-url", "http://localhost:8000"
      ],
      "env": {
        "GITVANE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

### 3. Cursor

Add to `.cursor/mcp.json` or Global Cursor Settings:

```json
{
  "mcpServers": {
    "gitvane": {
      "command": "uvx",
      "args": [
        "gitvane-mcp",
        "--server-url", "http://localhost:8000"
      ],
      "env": {
        "GITVANE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

### 4. Claude Code

Run the Claude Code CLI command:

```bash
claude mcp add gitvane -- uvx gitvane-mcp --server-url http://localhost:8000
```

Or configure via `.claude.json`:

```json
{
  "mcpServers": {
    "gitvane": {
      "command": "uvx",
      "args": ["gitvane-mcp", "--server-url", "http://localhost:8000"],
      "env": {
        "GITVANE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

### 5. Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "gitvane": {
      "command": "uvx",
      "args": [
        "gitvane-mcp",
        "--server-url", "http://localhost:8000"
      ],
      "env": {
        "GITVANE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

---

### 6. OpenAI Codex / Custom MCP Hosts

Configure stdio transport command:

```json
{
  "command": "uvx",
  "args": ["gitvane-mcp", "--server-url", "http://localhost:8000"],
  "env": {
    "GITVANE_API_KEY": "${GITVANE_API_KEY}"
  }
}
```

---

## Tool Reference

### `gitvane_analyze_impact`
Predicts the ripple impact of proposed or uncommitted code changes across the repository.

| Argument | Type | Description |
|---|---|---|
| `changed_files` | `list[str]` (optional) | List of modified file paths |
| `diff` | `str` (optional) | Raw git diff string. If omitted along with `changed_files`, working tree diff is auto-collected. |
| `top_k` | `int` (default `20`) | Max number of impacted files to return |
| `include_explanation` | `bool` (default `true`) | Generate LLM reasoning explanation |
| `max_dependency_depth` | `int` (default `3`) | Maximum graph traversal depth |
| `base_ref` | `str` (optional) | Base Git commit SHA / branch reference |
| `head_ref` | `str` (optional) | Head Git commit SHA / branch reference |
| `repo_id` | `str` (optional) | Target repository UUID/name override |

### `gitvane_recommend_tests`
Recommends relevant test files to execute for modified files.

| Argument | Type | Description |
|---|---|---|
| `changed_files` | `list[str]` (optional) | List of modified file paths |
| `impacted_files` | `list[str]` (optional) | List of upstream impacted file paths |
| `top_k` | `int` (default `10`) | Max number of test files to return |
| `repo_id` | `str` (optional) | Target repository UUID/name override |

### `gitvane_get_file_risk`
Retrieves architectural risk rankings, cyclomatic complexity, churn, and dependency fan-in scores.

| Argument | Type | Description |
|---|---|---|
| `file_path` | `str` (optional) | Specific file path to query |
| `top_k` | `int` (default `20`) | Top $K$ highest-risk files |
| `language` | `str` (optional) | Filter by language (e.g. `python`, `typescript`) |
| `include_tests` | `bool` (default `false`) | Include test files in ranking |
| `repo_id` | `str` (optional) | Target repository UUID/name override |

---

## Testing & Quality

Run the test suite:

```bash
cd mcp
uv run pytest -q
```
