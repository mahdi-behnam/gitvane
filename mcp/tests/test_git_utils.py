"""
Unit tests for git utilities, URL normalization, and diff parsing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from gitvane_mcp.git_utils import (
    extract_repo_name,
    get_changed_files,
    get_remote_url,
    get_repo_root,
    get_untracked_files,
    get_working_tree_diff,
    merge_line_ranges,
    normalize_repo_url,
    parse_diff_to_changed_files,
    run_git_command,
)


def test_normalize_repo_url() -> None:
    # SSH standard
    assert (
        normalize_repo_url("git@github.com:org/repo.git")
        == "https://github.com/org/repo"
    )
    # SSH protocol
    assert (
        normalize_repo_url("ssh://git@github.com:org/repo.git")
        == "https://github.com/org/repo"
    )
    # HTTPS with .git and trailing slash
    assert (
        normalize_repo_url("https://github.com/org/repo.git/")
        == "https://github.com/org/repo"
    )
    # git:// protocol
    assert (
        normalize_repo_url("git://github.com/org/repo.git")
        == "https://github.com/org/repo"
    )
    # Empty string
    assert normalize_repo_url("") == ""


def test_extract_repo_name() -> None:
    assert extract_repo_name("https://github.com/org/my-project.git") == "my-project"
    assert extract_repo_name("git@gitlab.com:team/subgroup/app.git") == "app"


def test_merge_line_ranges() -> None:
    # Empty
    assert merge_line_ranges([]) == []
    # Overlapping
    assert merge_line_ranges([(1, 5), (3, 8), (10, 12)]) == [(1, 8), (10, 12)]
    # Consecutive / adjacent
    assert merge_line_ranges([(1, 5), (6, 10)]) == [(1, 10)]
    # Disjoint
    assert merge_line_ranges([(1, 2), (10, 20)]) == [(1, 2), (10, 20)]


def test_parse_unified_diff() -> None:
    sample_diff = """diff --git a/app/main.py b/app/main.py
index e69de29..d95f3ad 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,5 +10,7 @@ def process():
     line_a()
+    line_b()
+    line_c()
     line_d()
diff --git a/app/new_file.py b/app/new_file.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/app/new_file.py
@@ -0,0 +1,15 @@
+def test_something():
+    pass
diff --git a/app/deleted_file.py b/app/deleted_file.py
deleted file mode 100644
index e69de29..0000000
--- a/app/deleted_file.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def old():
-    pass
diff --git a/app/renamed.py b/app/renamed_new.py
similarity index 100%
rename from app/renamed.py
rename to app/renamed_new.py
"""
    parsed = parse_diff_to_changed_files(sample_diff)
    assert len(parsed) == 4

    # Modified file
    assert parsed[0]["path"] == "app/main.py"
    assert parsed[0]["change_type"] == "modified"
    assert parsed[0]["changed_lines"] == [(10, 16)]

    # New file
    assert parsed[1]["path"] == "app/new_file.py"
    assert parsed[1]["change_type"] == "added"
    assert parsed[1]["changed_lines"] == [(1, 15)]

    # Deleted file
    assert parsed[2]["path"] == "app/deleted_file.py"
    assert parsed[2]["change_type"] == "deleted"

    # Renamed file
    assert parsed[3]["path"] == "app/renamed_new.py"
    assert parsed[3]["old_path"] == "app/renamed.py"


def test_parse_diff_empty() -> None:
    assert parse_diff_to_changed_files("") == []
    assert parse_diff_to_changed_files("   ") == []


def test_run_git_command_exception() -> None:
    with patch("subprocess.run", side_effect=OSError("Command not found")):
        code, stdout, stderr = run_git_command(["status"])
        assert code == -1
        assert "Command not found" in stderr


def test_get_remote_url_fallbacks(tmp_path: Path) -> None:
    # 1. Non-git directory
    assert get_remote_url(tmp_path) is None

    # 2. Mock fallback to remote -v
    with patch(
        "gitvane_mcp.git_utils.run_git_command",
        side_effect=[
            (1, "", "no config"),
            (1, "", "no get-url"),
            (0, "origin https://github.com/fallback/repo.git (fetch)\norigin https://github.com/fallback/repo.git (push)", ""),
        ],
    ):
        url = get_remote_url(tmp_path)
        assert url == "https://github.com/fallback/repo.git"


def test_git_repo_operations(temp_git_repo: Path) -> None:
    # Test repo root detection
    root = get_repo_root(temp_git_repo)
    assert root is not None
    assert root.resolve() == temp_git_repo.resolve()

    # Test remote url
    remote_url = get_remote_url(temp_git_repo)
    assert remote_url == "https://github.com/org/test_repo.git"

    # Make uncommitted modifications
    main_py = temp_git_repo / "main.py"
    main_py.write_text("def hello():\n    return 'modified'\n", encoding="utf-8")

    # Add a new untracked file
    utils_py = temp_git_repo / "utils.py"
    utils_py.write_text("def util(): pass\n", encoding="utf-8")

    # Test diff
    diff = get_working_tree_diff(temp_git_repo)
    assert "diff --git a/main.py b/main.py" in diff
    assert "modified" in diff

    # Test untracked
    untracked = get_untracked_files(temp_git_repo)
    assert "utils.py" in untracked

    # Test changed files
    changed = get_changed_files(temp_git_repo)
    paths = {c["path"] for c in changed}
    assert "main.py" in paths
    assert "utils.py" in paths
