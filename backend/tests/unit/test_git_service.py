"""Unit tests for app.services.git_service.GitService.

Tests that do not require a real Git repository use MagicMock
to isolate the GitPython interface.  Only is_binary_file (which
operates on plain bytes / files) is tested without mocking.
"""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from app.core.errors import GitOperationError, PrivateRepositoryNotSupportedError
from app.services.git_service import GitService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def svc() -> GitService:
    return GitService()


def _make_mock_repo() -> MagicMock:
    """Return a minimal GitPython Repo mock."""
    repo = MagicMock()
    return repo


# ---------------------------------------------------------------------------
# get_current_sha
# ---------------------------------------------------------------------------


def test_get_current_sha_returns_hexsha(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.head.commit.hexsha = "abc123def456" * 2  # 24-char fake SHA

    result = svc.get_current_sha(repo)

    assert result == "abc123def456abc123def456"


def test_get_current_sha_raises_on_error(svc: GitService) -> None:
    # Configure repo.head.commit to raise when accessed, which forces the
    # service's try/except to catch and re-raise as GitOperationError.
    repo = MagicMock()
    type(repo.head).commit = PropertyMock(
        side_effect=Exception("detached HEAD")
    )

    with pytest.raises(
        GitOperationError, match="Failed to retrieve current commit SHA"
    ):
        svc.get_current_sha(repo)


# ---------------------------------------------------------------------------
# get_default_branch
# ---------------------------------------------------------------------------


def test_get_default_branch_from_remote_head(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.git.symbolic_ref.return_value = "refs/remotes/origin/HEAD -> origin/main"

    result = svc.get_default_branch(repo)

    assert result == "main"


def test_get_default_branch_falls_back_to_active_branch(svc: GitService) -> None:
    repo = _make_mock_repo()
    # Simulate symbolic_ref failing
    repo.git.symbolic_ref.side_effect = Exception("no remote HEAD")
    repo.active_branch.name = "develop"

    result = svc.get_default_branch(repo)

    assert result == "develop"


def test_get_default_branch_falls_back_to_common_names(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.git.symbolic_ref.side_effect = Exception("no remote HEAD")
    # Make active_branch itself raise TypeError when accessed, which forces
    # the service into the `except` block that checks repo.heads.
    type(repo).active_branch = PropertyMock(
        side_effect=TypeError("HEAD is a detached symbolic reference")
    )
    # heads list contains 'main'; `if name in repo.heads` will be True
    # and the service returns the name string directly.
    repo.heads = ["main"]

    result = svc.get_default_branch(repo)

    assert result == "main"


# ---------------------------------------------------------------------------
# checkout_ref
# ---------------------------------------------------------------------------


def test_checkout_ref_calls_git_checkout(svc: GitService) -> None:
    repo = _make_mock_repo()

    svc.checkout_ref(repo, "feature/my-branch")

    repo.git.checkout.assert_called_once_with("feature/my-branch")


def test_checkout_ref_raises_on_failure(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.git.checkout.side_effect = Exception("branch not found")

    with pytest.raises(GitOperationError, match="Failed to checkout ref"):
        svc.checkout_ref(repo, "nonexistent")


# ---------------------------------------------------------------------------
# iter_commits
# ---------------------------------------------------------------------------


def test_iter_commits_respects_max_count(svc: GitService) -> None:
    repo = _make_mock_repo()
    fake_commits = [MagicMock() for _ in range(3)]
    repo.iter_commits.return_value = iter(fake_commits)

    result = svc.iter_commits(repo, max_count=3)

    repo.iter_commits.assert_called_once_with(max_count=3)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# list_tracked_files
# ---------------------------------------------------------------------------


def test_list_tracked_files_head(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.git.ls_files.return_value = "app/main.py\napp/core/config.py\n"

    result = svc.list_tracked_files(repo)

    assert result == ["app/main.py", "app/core/config.py"]


def test_list_tracked_files_at_ref(svc: GitService) -> None:
    repo = _make_mock_repo()
    repo.git.ls_tree.return_value = "README.md\nsrc/index.ts\n"

    result = svc.list_tracked_files(repo, ref="abc123")

    repo.git.ls_tree.assert_called_once_with("-r", "--name-only", "abc123")
    assert "README.md" in result
    assert "src/index.ts" in result


# ---------------------------------------------------------------------------
# is_binary_file
# ---------------------------------------------------------------------------


def test_is_binary_file_detects_null_bytes_in_content() -> None:
    svc = GitService()
    assert svc.is_binary_file(content=b"PK\x03\x04\x00\x00") is True


def test_is_binary_file_detects_text_content() -> None:
    svc = GitService()
    assert svc.is_binary_file(content=b"def hello():\n    pass\n") is False


def test_is_binary_file_reads_from_path(tmp_path: Path) -> None:
    svc = GitService()
    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03")

    assert svc.is_binary_file(file_path=binary_file) is True


def test_is_binary_file_reads_text_from_path(tmp_path: Path) -> None:
    svc = GitService()
    text_file = tmp_path / "source.py"
    text_file.write_text("print('hello')\n", encoding="utf-8")

    assert svc.is_binary_file(file_path=text_file) is False


def test_is_binary_file_returns_false_when_no_args() -> None:
    svc = GitService()
    # No content and no path → defaults to False (cannot determine)
    assert svc.is_binary_file() is False


# ---------------------------------------------------------------------------
# verify_public_accessibility
# ---------------------------------------------------------------------------


@patch("git.cmd.Git")
def test_verify_public_accessibility_success(mock_git_cls: MagicMock, svc: GitService) -> None:
    mock_git_instance = MagicMock()
    mock_git_cls.return_value = mock_git_instance

    svc.verify_public_accessibility("https://github.com/public/repo.git")

    mock_git_instance.ls_remote.assert_called_once_with(
        "--symref",
        "https://github.com/public/repo.git",
        "HEAD",
        env={"GIT_TERMINAL_PROMPT": "0"},
    )


@patch("git.cmd.Git")
def test_verify_public_accessibility_private_error(mock_git_cls: MagicMock, svc: GitService) -> None:
    from git.exc import GitCommandError

    mock_git_instance = MagicMock()
    exc = GitCommandError(
        command=["git", "ls-remote"],
        status=128,
        stderr="fatal: could not read Username: terminal prompts disabled",
    )
    mock_git_instance.ls_remote.side_effect = exc
    mock_git_cls.return_value = mock_git_instance

    with pytest.raises(PrivateRepositoryNotSupportedError):
        svc.verify_public_accessibility("https://github.com/private/repo.git")


@patch("git.cmd.Git")
def test_verify_public_accessibility_general_error(mock_git_cls: MagicMock, svc: GitService) -> None:
    from git.exc import GitCommandError

    mock_git_instance = MagicMock()
    exc = GitCommandError(
        command=["git", "ls-remote"],
        status=128,
        stderr="fatal: remote error: Some other git error",
    )
    mock_git_instance.ls_remote.side_effect = exc
    mock_git_cls.return_value = mock_git_instance

    with pytest.raises(GitOperationError, match="Git remote check failed"):
        svc.verify_public_accessibility("https://github.com/invalid/repo.git")


def test_list_repository_refs_returns_branches_tags_commits(svc: GitService) -> None:
    repo = MagicMock()

    # Mock branch head
    head = MagicMock()
    head.name = "main"
    head_commit = MagicMock()
    head_commit.hexsha = "abc123456789"
    head_commit.summary = "Initial commit"
    head.commit = head_commit
    repo.heads = [head]

    # Mock tag
    tag = MagicMock()
    tag.name = "v1.0.0"
    tag_commit = MagicMock()
    tag_commit.hexsha = "def987654321"
    tag_commit.summary = "Release v1.0.0"
    tag.commit = tag_commit
    repo.tags = [tag]


    # Mock commits
    commit1 = MagicMock()
    commit1.hexsha = "abc123456789"
    commit1.summary = "Initial commit"
    commit1.authored_date = 1600000000

    commit2 = MagicMock()
    commit2.hexsha = "fed543210987"
    commit2.summary = "Fix bug in parser"
    commit2.authored_date = 1600000500

    repo.iter_commits.return_value = [commit1, commit2]

    results = svc.list_repository_refs(repo)

    assert len(results) == 3
    assert results[0]["name"] == "main"
    assert results[0]["ref_type"] == "branch"
    assert results[1]["name"] == "v1.0.0"
    assert results[1]["ref_type"] == "tag"
    assert results[2]["name"] == "fed5432"
    assert results[2]["ref_type"] == "commit"


def test_list_repository_refs_filters_by_query(svc: GitService) -> None:
    repo = MagicMock()

    head = MagicMock()
    head.name = "feature-login"
    head.commit.hexsha = "111222333444"
    head.commit.summary = "Add login screen"

    head2 = MagicMock()
    head2.name = "main"
    head2.commit.hexsha = "555666777888"
    head2.commit.summary = "Main branch commit"

    repo.heads = [head, head2]
    repo.tags = []
    repo.iter_commits.return_value = []

    results = svc.list_repository_refs(repo, query="login")

    assert len(results) == 1
    assert results[0]["name"] == "feature-login"


def test_fetch_and_pull_ref_success(svc: GitService, tmp_path: Path) -> None:
    with patch.object(svc, "open_repository") as mock_open:
        mock_repo = MagicMock()
        mock_head = MagicMock()
        mock_head.commit.hexsha = "abcdef1234567890abcdef1234567890abcdef12"
        mock_repo.head = mock_head
        mock_repo.heads = {"main": MagicMock()}
        mock_open.return_value = mock_repo

        with patch.object(svc.validator, "validate_path_containment"):
            with patch.object(svc.validator, "validate_repository_limits"):
                result_sha = svc.fetch_and_pull_ref(
                    local_path=tmp_path,
                    ref="main",
                    clone_url="https://github.com/org/repo.git",
                )

        assert result_sha == "abcdef1234567890abcdef1234567890abcdef12"
        mock_repo.git.fetch.assert_called_once()


