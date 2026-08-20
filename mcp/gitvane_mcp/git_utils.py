"""
Git utilities for local workspace inspection, diff extraction, and repository resolution.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional


def run_git_command(args: list[str], cwd: Optional[Path | str] = None) -> tuple[int, str, str]:
    """Execute a git command in the specified directory."""
    try:
        process = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return process.returncode, process.stdout.strip(), process.stderr.strip()
    except Exception as exc:
        return -1, "", str(exc)


def get_repo_root(cwd: Optional[Path | str] = None) -> Optional[Path]:
    """Find the root directory of the git working tree."""
    code, stdout, _ = run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    if code == 0 and stdout:
        return Path(stdout).resolve()
    return None


def get_remote_url(cwd: Optional[Path | str] = None, remote: str = "origin") -> Optional[str]:
    """Get the remote repository URL for the specified remote name (default: origin)."""
    # Try git config --get remote.<remote>.url
    code, stdout, _ = run_git_command(["config", "--get", f"remote.{remote}.url"], cwd=cwd)
    if code == 0 and stdout:
        return stdout

    # Fallback to git remote get-url <remote>
    code, stdout, _ = run_git_command(["remote", "get-url", remote], cwd=cwd)
    if code == 0 and stdout:
        return stdout

    # Fallback: list all remotes and pick the first URL
    code, stdout, _ = run_git_command(["remote", "-v"], cwd=cwd)
    if code == 0 and stdout:
        lines = stdout.splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return None


def normalize_repo_url(url: str) -> str:
    """
    Normalize git remote URLs across SSH, HTTPS, and git protocols to a clean canonical format.
    Example:
      - 'git@github.com:org/repo.git' -> 'https://github.com/org/repo'
      - 'ssh://git@github.com/org/repo.git' -> 'https://github.com/org/repo'
      - 'https://github.com/org/repo.git/' -> 'https://github.com/org/repo'
    """
    raw = url.strip()
    if not raw:
        return ""

    # Remove trailing slashes and .git suffix
    cleaned = raw.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    # Handle SSH format: git@hostname:owner/repo
    ssh_match = re.match(r"^(?:ssh://)?git@([^:]+):(.+)$", cleaned)
    if ssh_match:
        host, path = ssh_match.groups()
        return f"https://{host.lower()}/{path.lstrip('/')}"

    # Handle git:// format
    if cleaned.startswith("git://"):
        return "https://" + cleaned[len("git://") :]

    # Handle standard https:// or http:// format
    return cleaned


def extract_repo_name(url_or_path: str) -> str:
    """Extract repository name from remote URL or local path."""
    normalized = normalize_repo_url(url_or_path)
    if "/" in normalized:
        return normalized.split("/")[-1]
    path_obj = Path(url_or_path)
    return path_obj.name


def get_working_tree_diff(cwd: Optional[Path | str] = None) -> str:
    """
    Extract the local uncommitted working tree diff against HEAD.
    If HEAD is not valid (e.g., initial empty repo), fall back to git diff --cached or git diff.
    """
    # Primary: git diff HEAD (includes staged + unstaged changes)
    code, stdout, _ = run_git_command(["diff", "HEAD"], cwd=cwd)
    if code == 0 and stdout:
        return stdout

    # Fallback 1: git diff --cached (staged changes)
    code_staged, stdout_staged, _ = run_git_command(["diff", "--cached"], cwd=cwd)
    # Fallback 2: git diff (unstaged changes)
    code_unstaged, stdout_unstaged, _ = run_git_command(["diff"], cwd=cwd)

    diffs: list[str] = []
    if code_staged == 0 and stdout_staged:
        diffs.append(stdout_staged)
    if code_unstaged == 0 and stdout_unstaged:
        diffs.append(stdout_unstaged)

    return "\n".join(diffs)


def merge_line_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or consecutive line ranges."""
    if not ranges:
        return []
    sorted_ranges = sorted(ranges, key=lambda r: (r[0], r[1]))
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


HUNK_HEADER_RE = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)


def parse_diff_to_changed_files(raw_diff: str) -> list[dict[str, Any]]:
    """
    Parse a standard unified git diff into a list of ChangedFileInput dictionaries:
    [
        {
            "path": "path/to/file.py",
            "change_type": "modified" | "added" | "deleted",
            "changed_lines": [(start, end), ...],
            "old_path": None | "old/path.py"
        }
    ]
    """
    if not raw_diff or not raw_diff.strip():
        return []

    files: list[dict[str, Any]] = []
    current_file: Optional[dict[str, Any]] = None
    current_ranges: list[tuple[int, int]] = []

    lines = raw_diff.splitlines()

    for line in lines:
        if line.startswith("diff --git "):
            if current_file:
                current_file["changed_lines"] = merge_line_ranges(current_ranges)
                files.append(current_file)
            current_ranges = []

            # Parse path from 'diff --git a/path b/path'
            parts = line[len("diff --git ") :].split(" ")
            path_a = parts[0][2:] if parts[0].startswith("a/") else parts[0]
            path_b = parts[1][2:] if len(parts) > 1 and parts[1].startswith("b/") else path_a

            current_file = {
                "path": path_b,
                "change_type": "modified",
                "changed_lines": [],
                "old_path": None,
            }
            continue

        if not current_file:
            continue

        if line.startswith("new file mode "):
            current_file["change_type"] = "added"
        elif line.startswith("deleted file mode "):
            current_file["change_type"] = "deleted"
        elif line.startswith("rename from "):
            current_file["old_path"] = line[len("rename from ") :].strip()
            current_file["change_type"] = "renamed"
        elif line.startswith("rename to "):
            current_file["path"] = line[len("rename to ") :].strip()
        elif line.startswith("--- "):
            old_p = line[4:].strip()
            if old_p == "/dev/null":
                current_file["change_type"] = "added"
            elif old_p.startswith("a/"):
                current_file["old_path"] = old_p[2:]
        elif line.startswith("+++ "):
            new_p = line[4:].strip()
            if new_p == "/dev/null":
                current_file["change_type"] = "deleted"
            elif new_p.startswith("b/"):
                current_file["path"] = new_p[2:]
        elif line.startswith("@@"):
            match = HUNK_HEADER_RE.match(line)
            if match:
                new_start = int(match.group("new_start"))
                new_count_str = match.group("new_count")
                new_count = int(new_count_str) if new_count_str is not None else 1
                if new_count == 0:
                    current_ranges.append((new_start, new_start))
                else:
                    current_ranges.append((new_start, new_start + new_count - 1))

    if current_file:
        current_file["changed_lines"] = merge_line_ranges(current_ranges)
        files.append(current_file)

    return files


def get_untracked_files(cwd: Optional[Path | str] = None) -> list[str]:
    """Retrieve list of untracked files in the working copy."""
    code, stdout, _ = run_git_command(["ls-files", "--others", "--exclude-standard"], cwd=cwd)
    if code == 0 and stdout:
        return [f.strip() for f in stdout.splitlines() if f.strip()]
    return []


def get_changed_files(cwd: Optional[Path | str] = None) -> list[dict[str, Any]]:
    """
    Get full list of changed files (diff-tracked changes + untracked files) in the working copy.
    """
    diff = get_working_tree_diff(cwd=cwd)
    changed = parse_diff_to_changed_files(diff)
    existing_paths = {item["path"] for item in changed}

    # Add untracked files
    untracked = get_untracked_files(cwd=cwd)
    for u_path in untracked:
        if u_path not in existing_paths:
            changed.append({
                "path": u_path,
                "change_type": "added",
                "changed_lines": [],
                "old_path": None,
            })
            existing_paths.add(u_path)

    return changed
