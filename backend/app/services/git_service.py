import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import git

from app.core.errors import GitOperationError


class GitService:
    """Service to handle Git operations using GitPython"""

    def clone_repository(
        self, clone_url: str, target_path: str | Path, branch: Optional[str] = None
    ) -> git.Repo:
        """Clones a remote repository to the specified target path."""
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            kwargs = {}
            if branch:
                kwargs["branch"] = branch

            repo = git.Repo.clone_from(clone_url, str(target_path), **kwargs)  # type: ignore
            return repo
        except Exception as e:
            raise GitOperationError(f"Failed to clone repository: {str(e)}") from e

    def open_repository(self, local_path: str | Path) -> git.Repo:
        """Opens an existing local repository."""
        try:
            return git.Repo(str(local_path))
        except Exception as e:
            raise GitOperationError(f"Failed to open repository: {str(e)}") from e

    def get_current_sha(self, repo: git.Repo) -> str:
        """Returns the current commit SHA of the repository."""
        try:
            return str(repo.head.commit.hexsha)
        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve current commit SHA: {str(e)}"
            ) from e

    def get_default_branch(self, repo: git.Repo) -> str:
        """Returns the default branch of the repository (e.g. main/master)."""
        try:
            # Check remote HEAD reference first
            try:
                ref = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
                return str(ref.split("/")[-1])
            except Exception:
                pass

            # Fallback to active branch name or common defaults
            try:
                return str(repo.active_branch.name)
            except Exception:
                # If in detached HEAD state and no remote HEAD found
                for name in ["main", "master", "development"]:
                    if name in repo.heads:
                        return name
                if repo.heads:
                    return str(repo.heads[0].name)
                return "main"
        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve default branch: {str(e)}"
            ) from e

    def checkout_ref(self, repo: git.Repo, ref: str) -> None:
        """Checks out the specified ref (branch, tag, or commit SHA)."""
        try:
            repo.git.checkout(ref)
        except Exception as e:
            raise GitOperationError(f"Failed to checkout ref '{ref}': {str(e)}") from e

    def get_diff_between_refs(
        self, repo: git.Repo, base_ref: str, head_ref: str
    ) -> str:
        """Returns the unified diff text between two refs."""
        try:
            return str(repo.git.diff(base_ref, head_ref))
        except Exception as e:
            raise GitOperationError(
                f"Failed to get diff between '{base_ref}' and '{head_ref}': {str(e)}"
            ) from e

    def get_raw_diff(self, repo: git.Repo, ref_or_commit: str) -> str:
        """Returns the raw unified diff of a commit against its parent(s)."""
        try:
            commit_obj = repo.commit(ref_or_commit)
            if commit_obj.parents:
                return str(
                    repo.git.diff(commit_obj.parents[0].hexsha, commit_obj.hexsha)
                )
            else:
                # Initial commit with no parent; diff against the empty tree
                return str(repo.git.diff(git.NULL_TREE, commit_obj.hexsha))
        except Exception as e:
            raise GitOperationError(
                f"Failed to get raw diff for '{ref_or_commit}': {str(e)}"
            ) from e

    def get_changed_files_between_refs(
        self, repo: git.Repo, base_ref: str, head_ref: str
    ) -> List[Dict[str, Any]]:
        """Returns a list of changed files with change types between two refs."""
        try:
            base_commit = repo.commit(base_ref)
            head_commit = repo.commit(head_ref)
            diffs = base_commit.diff(head_commit)

            changed_files = []
            for diff in diffs:
                change_type = "modified"
                if diff.change_type == "A":
                    change_type = "added"
                elif diff.change_type == "D":
                    change_type = "deleted"
                elif diff.change_type == "R":
                    change_type = "renamed"

                changed_files.append(
                    {
                        "path": diff.b_path
                        if change_type != "deleted"
                        else diff.a_path,
                        "change_type": change_type,
                        "old_path": diff.a_path if change_type == "renamed" else None,
                    }
                )
            return changed_files
        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve changed files between '{base_ref}' and '{head_ref}': {str(e)}"
            ) from e

    def iter_commits(self, repo: git.Repo, max_count: int = 500) -> List[git.Commit]:
        """Returns an iterator over recent commits."""
        try:
            return list(repo.iter_commits(max_count=max_count))
        except Exception as e:
            raise GitOperationError(f"Failed to iterate commits: {str(e)}") from e

    def get_commit_metadata(self, repo: git.Repo, commit_sha: str) -> Dict[str, Any]:
        """Retrieves structured metadata for a specific commit."""
        try:
            commit = repo.commit(commit_sha)

            # Fetch insertions/deletions stats safely
            try:
                stats = commit.stats.total
                insertions = stats.get("insertions", 0)
                deletions = stats.get("deletions", 0)
            except Exception:
                insertions = 0
                deletions = 0

            return {
                "sha": commit.hexsha,
                "parent_sha": commit.parents[0].hexsha if commit.parents else None,
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "author_date": datetime.fromtimestamp(commit.authored_date),
                "message": commit.message,
                "insertions": insertions,
                "deletions": deletions,
            }
        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve metadata for commit '{commit_sha}': {str(e)}"
            ) from e

    def get_file_content_at_ref(
        self, repo: git.Repo, file_path: str, ref: str
    ) -> bytes:
        """Returns the file content bytes at a specific ref."""
        try:
            return cast(bytes, repo.git.show(f"{ref}:{file_path}", stdout_as_string=False))
        except Exception as e:
            raise GitOperationError(
                f"Failed to retrieve content for '{file_path}' at ref '{ref}': {str(e)}"
            ) from e

    def list_tracked_files(
        self, repo: git.Repo, ref: Optional[str] = None
    ) -> List[str]:
        """Lists all files tracked by git at the specified ref or HEAD."""
        try:
            if ref:
                output = repo.git.ls_tree("-r", "--name-only", ref)
            else:
                output = repo.git.ls_files()
            return cast(str, output).splitlines()
        except Exception as e:
            raise GitOperationError(f"Failed to list tracked files: {str(e)}") from e

    def is_binary_file(
        self, file_path: Optional[str | Path] = None, content: Optional[bytes] = None
    ) -> bool:
        """Checks if a file or block of bytes is binary by searching for null bytes."""
        if content is not None:
            return b"\x00" in content[:8000]

        if file_path is not None:
            try:
                with open(file_path, "rb") as f:
                    chunk = f.read(8000)
                    return b"\x00" in chunk
            except Exception:
                pass
        return False
