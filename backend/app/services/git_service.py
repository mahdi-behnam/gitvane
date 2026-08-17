import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import git

from app.core.errors import (
    GitOperationError,
    GitVaneError,
    PrivateRepositoryNotSupportedError,
)
from app.services.security_validator import RepositoryIngestionValidator


class GitService:
    """Service to handle Git operations using GitPython with Security Boundary enforcement."""

    def __init__(self, validator: Optional[RepositoryIngestionValidator] = None) -> None:
        self.validator = validator or RepositoryIngestionValidator()

    def _get_authenticated_url(self, url: str, pat: Optional[str] = None) -> str:
        if not pat:
            return url
        if url.startswith("https://"):
            return f"https://{pat}@{url[8:]}"
        elif url.startswith("http://"):
            return f"http://{pat}@{url[7:]}"
        return url

    def _sanitize_error_message(self, err_msg: str, pat: Optional[str] = None) -> str:
        if pat:
            err_msg = err_msg.replace(pat, "****")
        err_msg = re.sub(r"https?://[^@]+@", "https://****@", err_msg)
        return err_msg

    def verify_public_accessibility(self, clone_url: str, pat: Optional[str] = None) -> None:
        """Verifies if the remote repository is publicly accessible and safe from SSRF."""
        # 1. Enforce scheme & SSRF IP validation
        self.validator.validate_dns_and_ssrf(clone_url)

        auth_url = self._get_authenticated_url(clone_url, pat)
        try:
            g = git.cmd.Git()
            g.ls_remote("--symref", auth_url, "HEAD", env={"GIT_TERMINAL_PROMPT": "0"})
        except GitVaneError:
            raise
        except git.exc.GitCommandError as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            stderr_msg = self._sanitize_error_message(getattr(e, "stderr", "") or "", pat)
            combined_err = f"{err_msg}\n{stderr_msg}".lower()
            
            auth_indicators = [
                "terminal prompts disabled",
                "authentication failed",
                "could not read username",
                "permission denied",
            ]
            if any(indicator in combined_err for indicator in auth_indicators):
                raise PrivateRepositoryNotSupportedError(
                    self._sanitize_error_message("Private repositories are not yet supported. Please use a public repository URL.", pat)
                ) from e
            
            raise GitOperationError(f"Git remote check failed: {err_msg}") from e
        except Exception as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            raise GitOperationError(f"Git remote check failed: {err_msg}") from e

    def list_remote_branches(
        self, clone_url: str, pat: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Queries remote Git branches using ls-remote without cloning the repository.
        Enforces SSRF safety, checks accessibility, and returns branch information and default branch.
        """
        # 1. Enforce scheme & SSRF IP validation
        self.validator.validate_dns_and_ssrf(clone_url)

        auth_url = self._get_authenticated_url(clone_url, pat)
        env = self.validator.get_sandbox_execution_env()

        try:
            g = git.cmd.Git()
            raw_heads = g.ls_remote("--heads", auth_url, env=env)

            default_branch: Optional[str] = None
            try:
                raw_symref = g.ls_remote("--symref", auth_url, "HEAD", env=env)
                for line in raw_symref.splitlines():
                    line = line.strip()
                    if line.startswith("ref: refs/heads/"):
                        parts = line.split()
                        if len(parts) >= 2:
                            default_branch = parts[1].replace("refs/heads/", "")
                            break
            except Exception:
                pass

            results: List[Dict[str, Any]] = []
            seen_branches: set = set()

            for line in raw_heads.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    sha = parts[0].strip()
                    ref = parts[1].strip()
                    if ref.startswith("refs/heads/"):
                        branch_name = ref.replace("refs/heads/", "")
                        if branch_name not in seen_branches:
                            seen_branches.add(branch_name)
                            results.append({
                                "name": branch_name,
                                "ref_type": "branch",
                                "commit_sha": sha[:7] if sha else None,
                                "commit_message": None,
                                "commit_date": None,
                            })

            # Sort branches: default_branch first (if exists), then alphabetical
            if default_branch:
                results.sort(key=lambda b: (0 if b["name"] == default_branch else 1, b["name"]))
            else:
                results.sort(key=lambda b: b["name"])

            return {
                "branches": results,
                "default_branch": default_branch,
            }
        except GitVaneError:
            raise
        except git.exc.GitCommandError as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            stderr_msg = self._sanitize_error_message(getattr(e, "stderr", "") or "", pat)
            combined_err = f"{err_msg}\n{stderr_msg}".lower()

            auth_indicators = [
                "terminal prompts disabled",
                "authentication failed",
                "could not read username",
                "permission denied",
            ]
            if any(indicator in combined_err for indicator in auth_indicators):
                raise PrivateRepositoryNotSupportedError(
                    self._sanitize_error_message(
                        "Private repositories are not yet supported. Please use a public repository URL.",
                        pat,
                    )
                ) from e

            raise GitOperationError(f"Git remote branch lookup failed: {err_msg}") from e
        except Exception as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            raise GitOperationError(f"Git remote branch lookup failed: {err_msg}") from e

    def clone_repository(
        self, clone_url: str, target_path: str | Path, branch: Optional[str] = None, pat: Optional[str] = None
    ) -> git.Repo:
        """Clones a remote repository to the specified target path after security validation."""
        # 1. Workspace path containment validation
        target_path_obj = Path(target_path)
        self.validator.validate_path_containment(target_path_obj)

        # 2. SSRF protection validation
        self.validator.validate_dns_and_ssrf(clone_url)

        auth_url = self._get_authenticated_url(clone_url, pat)
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            kwargs = {}
            if branch:
                kwargs["branch"] = branch

            env = self.validator.get_sandbox_execution_env()
            repo = git.Repo.clone_from(auth_url, str(target_path), env=env, **kwargs)  # type: ignore

            # 3. Post-clone resource limit validation
            self.validator.validate_repository_limits(target_path)
            return repo
        except GitVaneError:
            raise
        except git.exc.GitCommandError as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            raise GitOperationError(f"Failed to clone repository: {err_msg}") from e
        except Exception as e:
            err_msg = self._sanitize_error_message(str(e), pat)
            raise GitOperationError(f"Failed to clone repository: {err_msg}") from e

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

    def resolve_ref_to_sha(self, repo_path: str | Path, ref: str) -> str:
        """Resolves a Git ref (branch, tag, symbolic ref, HEAD, or commit) to a 40-character hex SHA."""
        try:
            repo = self.open_repository(repo_path)
            try:
                commit = repo.commit(ref)
                return str(commit.hexsha)
            except Exception:
                if f"origin/{ref}" in repo.refs:
                    return str(repo.refs[f"origin/{ref}"].commit.hexsha)
                if ref in repo.heads:
                    return str(repo.heads[ref].commit.hexsha)
                if ref in repo.tags:
                    return str(repo.tags[ref].commit.hexsha)
                return str(repo.head.commit.hexsha)
        except Exception as e:
            raise GitOperationError(f"Failed to resolve ref '{ref}' to commit SHA: {str(e)}") from e

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
                f"Failed to retrieve changed files between "
                f"'{base_ref}' and '{head_ref}': {str(e)}"
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
            return cast(
                bytes, repo.git.show(f"{ref}:{file_path}", stdout_as_string=False)
            )
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

    def list_repository_refs(
        self,
        repo: git.Repo,
        query: str = "",
        limit: int = 50,
        ref_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists git refs (branches, tags, commits) matching an optional query string.
        Optimized for performance by bounding scanned commits and deduplicating results.
        """
        results: List[Dict[str, Any]] = []
        seen_names: set = set()
        q = query.strip().lower()

        # 1. Branches (refs/heads)
        if not ref_type or ref_type == "branch":
            try:
                for head in repo.heads:
                    name = head.name
                    if q and q not in name.lower():
                        continue
                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    commit_sha = ""
                    commit_msg = ""
                    try:
                        commit_sha = head.commit.hexsha[:7]
                        commit_msg = head.commit.summary
                    except Exception:
                        pass

                    if commit_sha:
                        seen_names.add(commit_sha[:7])
                        seen_names.add(commit_sha)

                    results.append({
                        "name": name,
                        "ref_type": "branch",
                        "commit_sha": commit_sha,
                        "commit_message": commit_msg,
                        "commit_date": None,
                    })
                    if len(results) >= limit:
                        return results
            except Exception:
                pass

        # 2. Tags (refs/tags)
        if not ref_type or ref_type == "tag":
            try:
                for tag in repo.tags:
                    name = tag.name
                    if q and q not in name.lower():
                        continue
                    if name in seen_names:
                        continue
                    seen_names.add(name)

                    commit_sha = ""
                    commit_msg = ""
                    try:
                        commit_sha = tag.commit.hexsha[:7]
                        commit_msg = tag.commit.summary
                    except Exception:
                        pass

                    if commit_sha:
                        seen_names.add(commit_sha[:7])
                        seen_names.add(commit_sha)

                    results.append({
                        "name": name,
                        "ref_type": "tag",
                        "commit_sha": commit_sha,
                        "commit_message": commit_msg,
                        "commit_date": None,
                    })

                    if len(results) >= limit:
                        return results
            except Exception:
                pass

        # 3. Recent Commits (bounded iteration for performance)
        if not ref_type or ref_type == "commit":
            try:
                max_scan = max(limit * 2, 100)
                commits = list(repo.iter_commits(max_count=max_scan))
                for c in commits:
                    short_sha = c.hexsha[:7]
                    full_sha = c.hexsha
                    msg = c.summary

                    if q:
                        matches = (
                            q in short_sha.lower()
                            or q in full_sha.lower()
                            or q in msg.lower()
                        )
                        if not matches:
                            continue

                    display_name = short_sha
                    if display_name in seen_names or full_sha in seen_names:
                        continue
                    seen_names.add(display_name)
                    seen_names.add(full_sha)


                    c_date = (
                        datetime.fromtimestamp(c.authored_date).isoformat()
                        if hasattr(c, "authored_date")
                        else None
                    )

                    results.append({
                        "name": display_name,
                        "ref_type": "commit",
                        "commit_sha": full_sha,
                        "commit_message": msg,
                        "commit_date": c_date,
                    })
                    if len(results) >= limit:
                        return results
            except Exception:
                pass

        return results[:limit]

