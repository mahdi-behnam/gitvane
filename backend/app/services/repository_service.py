import shutil
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import RepositoryNotFoundError
from app.core.security import validate_and_resolve_path
from app.core.security_utils import encrypt_pat, decrypt_pat
from app.db.models import Repository
from app.services.git_service import GitService


class RepositoryService:
    """Service to handle repository operations and directory structures"""

    def __init__(self, git_service: GitService) -> None:
        self.git_service = git_service

    async def create_repository(
        self,
        db: AsyncSession,
        owner_id: int,
        name: str,
        clone_url: str,
        branch: Optional[str] = None,
        local_path: Optional[str] = None,
        index_now: bool = False,
        pat: Optional[str] = None,
    ) -> Repository:
        """Register and clone (or adopt) a Git repository.

        If clone_url is provided, the repository is cloned into the workspace.
        If local_path is provided, that path is validated and adopted as-is.
        Both can be provided simultaneously; clone_url takes precedence for
        the actual Git operation.

        When index_now=True the repository status is set to 'indexing_queued'
        so clients can immediately trigger or observe indexing work.
        """
        # 1. Create a Repository instance
        repo_obj = Repository(
            name=name,
            clone_url=clone_url,
            status="pending",
            owner_id=owner_id,
        )
        if pat:
            repo_obj.encrypted_pat = encrypt_pat(pat)

        db.add(repo_obj)
        await db.flush()  # Populates repo_obj.id

        # 2. Determine target path
        if local_path:
            # Validate user provided path is within workspace
            target_path = validate_and_resolve_path(local_path)
        else:
            # Default path is in REPOLENS_WORKSPACE/repo_{id}
            workspace_dir = Path(settings.REPOLENS_WORKSPACE).resolve()
            target_path = workspace_dir / f"repo_{repo_obj.id}"
            validate_and_resolve_path(target_path)  # Security double-check

        try:
            # 3. Clone or open repository
            if clone_url:
                self.git_service.verify_public_accessibility(clone_url, pat=pat)
                # If target path already exists and is not empty, clean it
                if target_path.exists() and any(target_path.iterdir()):
                    shutil.rmtree(target_path)

                git_repo = self.git_service.clone_repository(
                    clone_url=clone_url, target_path=target_path, branch=branch, pat=pat
                )
            else:
                # If no clone_url, open existing repo at local_path
                git_repo = self.git_service.open_repository(target_path)

            current_sha = self.git_service.get_current_sha(git_repo)
            default_branch = self.git_service.get_default_branch(git_repo)

            # 4. Update repository properties
            repo_obj.local_path = str(target_path.as_posix())
            repo_obj.current_ref = current_sha
            repo_obj.default_branch = default_branch
            # When index_now is requested, mark as queued for the indexing API;
            # otherwise mark as ready.
            repo_obj.status = "indexing_queued" if index_now else "ready"

            await db.commit()
            await db.refresh(repo_obj)
            return repo_obj

        except Exception as e:
            # Rollback database changes and delete local clone folder if created
            await db.rollback()
            if clone_url and target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            raise e

    async def get_repository(
        self, db: AsyncSession, repository_id: UUID | str, owner_id: int
    ) -> Optional[Repository]:
        """Retrieves a single repository by ID and owner_id, or None if not found."""
        stmt = select(Repository).where(
            Repository.id == repository_id, Repository.owner_id == owner_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_repository_or_raise(
        self, db: AsyncSession, repository_id: UUID | str, owner_id: int
    ) -> Repository:
        """Retrieve a repository by ID, raising RepositoryNotFoundError if absent or not owned."""
        repo = await self.get_repository(db, repository_id, owner_id=owner_id)
        if repo is None:
            raise RepositoryNotFoundError(
                f"Repository with id={repository_id} does not exist"
            )
        return repo

    async def list_repositories(
        self, db: AsyncSession, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Repository]:
        """Lists registered repositories with pagination."""
        stmt = (
            select(Repository)
            .where(Repository.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(Repository.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_repositories(self, db: AsyncSession, owner_id: int) -> int:
        """Returns the total number of registered repositories."""
        stmt = (
            select(func.count())
            .select_from(Repository)
            .where(Repository.owner_id == owner_id)
        )
        result = await db.execute(stmt)
        return int(result.scalar_one())

    async def delete_repository(
        self, db: AsyncSession, repository_id: UUID | str, owner_id: int
    ) -> Optional[Repository]:
        """Deletes a repository record and its local clone folder.

        Returns the deleted object, or None if not found.
        """
        repo_obj = await self.get_repository(db, repository_id, owner_id=owner_id)
        if not repo_obj:
            return None

        # Clean local files
        if repo_obj.local_path:
            try:
                # Resolve and validate path before deleting to prevent traversal attacks
                resolved_path = validate_and_resolve_path(repo_obj.local_path)
                if resolved_path.exists():
                    shutil.rmtree(resolved_path)
            except Exception:
                # Log deletion failure but continue removing DB row
                pass

        await db.delete(repo_obj)
        await db.commit()
        return repo_obj

    async def delete_repository_or_raise(
        self, db: AsyncSession, repository_id: UUID | str, owner_id: int
    ) -> Repository:
        """Deletes a repository, raising RepositoryNotFoundError if not found."""
        repo_obj = await self.get_repository_or_raise(db, repository_id, owner_id=owner_id)

        if repo_obj.local_path:
            try:
                resolved_path = validate_and_resolve_path(repo_obj.local_path)
                if resolved_path.exists():
                    shutil.rmtree(resolved_path)
            except Exception:
                pass

        await db.delete(repo_obj)
        await db.commit()
        return repo_obj

    async def list_repository_refs(
        self,
        db: AsyncSession,
        repository_id: UUID | str,
        owner_id: int,
        query: str = "",
        limit: int = 50,
        ref_type: Optional[str] = None,
    ) -> List[dict]:
        """Lists git refs (branches, tags, commits) for a repository."""
        repo = await self.get_repository_or_raise(db, repository_id, owner_id=owner_id)
        if not repo.local_path:
            return []

        resolved_path = validate_and_resolve_path(repo.local_path)
        git_repo = self.git_service.open_repository(resolved_path)
        return self.git_service.list_repository_refs(
            repo=git_repo, query=query, limit=limit, ref_type=ref_type
        )

