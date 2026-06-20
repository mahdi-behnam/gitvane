from pathlib import Path

IGNORED_PATTERNS = {
    ".git/",
    "node_modules/",
    "dist/",
    "build/",
    "coverage/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".next/",
    "out/",
    "target/",
}

IGNORED_EXTENSIONS = {
    ".min.js",
    ".map",
    ".lock",
}

IGNORED_EXACT_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
}


def should_ignore_file(file_path: str | Path) -> bool:
    """Returns True if the file matches any of the ignored patterns, names, or extensions"""
    path_str = Path(file_path).as_posix()

    # Check directory patterns
    for pattern in IGNORED_PATTERNS:
        if pattern in path_str or f"/{pattern}" in path_str:
            return True

    name = Path(file_path).name
    # Check exact names
    if name in IGNORED_EXACT_NAMES:
        return True

    # Check suffixes/extensions
    for ext in IGNORED_EXTENSIONS:
        if name.endswith(ext):
            return True

    return False
