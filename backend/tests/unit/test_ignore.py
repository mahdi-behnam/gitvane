"""Unit tests for app.analysis.ignore.

Verifies that should_ignore_file correctly identifies files and directories
that should be skipped during indexing.
"""

import pytest

from app.analysis.ignore import should_ignore_file


@pytest.mark.parametrize(
    "path,expected",
    [
        # Ignored directory prefixes
        (".git/config", True),
        ("node_modules/lodash/index.js", True),
        ("dist/bundle.js", True),
        ("build/output.js", True),
        ("coverage/lcov.info", True),
        (".venv/lib/python3.11/site.py", True),
        ("venv/lib/site.py", True),
        ("__pycache__/module.cpython-311.pyc", True),
        (".pytest_cache/README.md", True),
        (".mypy_cache/3.11/module.json", True),
        (".ruff_cache/v1/CACHEDIR.TAG", True),
        (".next/server/app.js", True),
        ("out/static/bundle.js", True),
        ("target/debug/binary", True),
        # Ignored exact file names
        ("package-lock.json", True),
        ("yarn.lock", True),
        ("pnpm-lock.yaml", True),
        ("poetry.lock", True),
        # Ignored extensions / suffixes
        ("app.min.js", True),
        ("style.min.js", True),
        ("source.map", True),
        ("Pipfile.lock", True),
        # Files that should NOT be ignored
        ("app/main.py", False),
        ("src/index.ts", False),
        ("tests/test_health.py", False),
        ("README.md", False),
        ("docs/ARCHITECTURE.md", False),
        # Edge cases: nested but legitimate paths
        ("src/components/build_tools.py", False),
        ("src/coverage_report.py", False),
    ],
)
def test_should_ignore_file(path: str, expected: bool) -> None:
    assert should_ignore_file(path) is expected
