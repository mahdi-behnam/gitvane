"""Unit tests for RepositoryIngestionValidator and security boundaries."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import (
    InvalidPathError,
    ResourceLimitExceededError,
    SSRFValidationError,
)
from app.services.security_validator import RepositoryIngestionValidator


def test_url_scheme_validation():
    """Verify approved Git URL schemes pass and unapproved schemes raise SSRFValidationError."""
    validator = RepositoryIngestionValidator()

    # Approved schemes
    assert validator.validate_url_scheme("https://github.com/org/repo.git") == "https"
    assert validator.validate_url_scheme("http://git.example.com/repo.git") == "http"
    assert validator.validate_url_scheme("git://github.com/org/repo.git") == "git"
    assert validator.validate_url_scheme("ssh://git@github.com/org/repo.git") == "ssh"
    assert validator.validate_url_scheme("git@github.com:org/repo.git") == "ssh"

    # Disallowed schemes
    disallowed = [
        "file:///etc/passwd",
        "ftp://ftp.example.com/repo.git",
        "gopher://gopher.example.com/",
        "dict://dict.example.com/",
        "tftp://tftp.example.com/",
    ]
    for url in disallowed:
        with pytest.raises(SSRFValidationError):
            validator.validate_url_scheme(url)


def test_ssrf_ip_blocking():
    """Verify loopback, private networks, link-local, and cloud metadata IPs are rejected."""
    validator = RepositoryIngestionValidator()

    blocked_ips = [
        "127.0.0.1",
        "127.0.0.53",
        "::1",
        "10.0.0.1",
        "10.254.0.1",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.1.1",
        "192.168.100.50",
        "169.254.169.254",  # AWS / GCP / Azure metadata target
        "169.254.1.1",
        "fe80::1",
        "fc00::1",
        "100.100.100.100",  # Alibaba metadata
        "0.0.0.0",
    ]

    for ip in blocked_ips:
        with pytest.raises(SSRFValidationError):
            validator.validate_ip_safety(ip)

    # Public IP should pass
    validator.validate_ip_safety("8.8.8.8")
    validator.validate_ip_safety("140.82.121.4")  # GitHub public IP


def test_dns_ssrf_validation():
    """Verify DNS resolution safety checks reject domain names resolving to internal IPs."""
    validator = RepositoryIngestionValidator()

    # Simulate hostname resolving to private metadata IP
    mock_addr_info = [
        (2, 1, 6, "", ("169.254.169.254", 80)),
    ]

    with patch("socket.getaddrinfo", return_value=mock_addr_info):
        with pytest.raises(SSRFValidationError):
            validator.validate_dns_and_ssrf("https://internal-metadata-service.local/repo.git")


def test_ingestion_resource_limits(tmp_path: Path):
    """Verify resource limits enforce max file count, individual file size, and total clone size."""
    # Custom tight limits for testing
    validator = RepositoryIngestionValidator(
        max_clone_size_bytes=1000,
        max_file_count=3,
        max_file_size_bytes=400,
    )

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # 1. Test individual file size limit
    big_file = repo_dir / "large.txt"
    big_file.write_bytes(b"A" * 500)  # > 400 bytes limit

    with pytest.raises(ResourceLimitExceededError) as exc_info:
        validator.validate_repository_limits(repo_dir, base_sandbox_dir=tmp_path)
    assert "individual file size" in str(exc_info.value)

    big_file.unlink()

    # 2. Test nested file reports relative path without leaking host paths
    subdir = repo_dir / "docs" / "assets"
    subdir.mkdir(parents=True)
    nested_big_file = subdir / "video.mp4"
    nested_big_file.write_bytes(b"A" * 500)
    with pytest.raises(ResourceLimitExceededError) as exc_info:
        validator.validate_repository_limits(repo_dir, base_sandbox_dir=tmp_path)
    assert "File 'docs/assets/video.mp4' exceeds" in str(exc_info.value)
    assert str(tmp_path) not in str(exc_info.value)
    nested_big_file.unlink()

    # 3. Test .git internal packfile is excluded from individual file size limit
    git_pack_dir = repo_dir / ".git" / "objects" / "pack"
    git_pack_dir.mkdir(parents=True)
    git_pack_file = git_pack_dir / "pack-d7449f192e5fc19b51b22f1c5912fc8342e5de41.pack"
    git_pack_file.write_bytes(b"G" * 500)  # > 400 bytes limit, but inside .git

    # Small working tree file
    (repo_dir / "main.py").write_bytes(b"print('hello')")

    # Should succeed because .git packfile is not restricted by individual file size limit
    stats = validator.validate_repository_limits(repo_dir, base_sandbox_dir=tmp_path)
    assert stats["total_files"] == 2

    # But total clone size limit still enforces total bytes (including .git)
    tight_total_validator = RepositoryIngestionValidator(
        max_clone_size_bytes=400,  # 500 + 14 > 400
        max_file_count=10,
        max_file_size_bytes=1000,
    )
    with pytest.raises(ResourceLimitExceededError) as exc_info:
        tight_total_validator.validate_repository_limits(repo_dir, base_sandbox_dir=tmp_path)
    assert "Total repository size exceeds" in str(exc_info.value)

    # Cleanup .git pack file
    git_pack_file.unlink()
    (repo_dir / "main.py").unlink()

    # 4. Test max file count limit
    for i in range(4):
        (repo_dir / f"file_{i}.txt").write_bytes(b"hello")

    with pytest.raises(ResourceLimitExceededError) as exc_info:
        validator.validate_repository_limits(repo_dir, base_sandbox_dir=tmp_path)
    assert "file count" in str(exc_info.value)


def test_binary_file_filtering(tmp_path: Path):
    """Verify binary file detection and filtering policy."""
    validator = RepositoryIngestionValidator()

    # Null byte detection
    assert validator.is_binary_file(content=b"hello\x00world")
    assert not validator.is_binary_file(content=b"def foo(): return 42")

    # Extension check
    assert validator.is_binary_file(file_path="module.pyc")
    assert validator.is_binary_file(file_path="library.so")
    assert validator.is_binary_file(file_path="app.exe")
    assert validator.is_binary_file(file_path="archive.zip")
    assert not validator.is_binary_file(file_path="main.py")

    files = [
        Path("main.py"),
        Path("utils.pyc"),
        Path("image.png"),
        Path("README.md"),
    ]
    filtered = validator.filter_indexable_files(files)
    assert set(filtered) == {Path("main.py"), Path("README.md")}


def test_workspace_path_containment(tmp_path: Path):
    """Verify workspace path containment and directory traversal protection."""
    validator = RepositoryIngestionValidator()

    sandbox = tmp_path / "workspaces"
    sandbox.mkdir()

    valid_repo = sandbox / "repo_123"
    valid_repo.mkdir()

    # Valid containment
    resolved = validator.validate_path_containment(valid_repo, base_sandbox_dir=sandbox)
    assert resolved == valid_repo.resolve()

    # Directory traversal attempt
    traversal_path = sandbox / "../outside_file.txt"
    with pytest.raises(InvalidPathError):
        validator.validate_path_containment(traversal_path, base_sandbox_dir=sandbox)


def test_sandbox_execution_env():
    """Verify sanitized worker sandbox environment variables."""
    validator = RepositoryIngestionValidator()

    base_env = {
        "PATH": "/usr/bin",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "JWT_SECRET_KEY": "supersecret",
    }

    env = validator.get_sandbox_execution_env(base_env)

    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_ALLOW_PROTOCOL"] == "http:https:git:ssh"
    assert env["GIT_LFS_SKIP_SMUDGE"] == "1"
    assert "DATABASE_URL" not in env
    assert "JWT_SECRET_KEY" not in env
