import shutil
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import validate_and_resolve_path
from app.db.models import Repository
from app.services.git_service import GitService


class RepositoryService:
    """Service to handle repository operations and directory structures"""

    def __init__(self, git_service: GitService) -> None:
        self.git_service = git_service

    async def create_repository(
        self,
        db: AsyncSession,
        name: str,
        clone_url: str,
        branch: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> Repository:
        """Registers and clones a Git repository."""
        # 1. Create a Repository instance
        repo_obj = Repository(
            name=name,
            clone_url=clone_url,
            status="pending",
        )
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
                # If target path already exists and is not empty, clean it
                if target_path.exists() and any(target_path.iterdir()):
                    shutil.rmtree(target_path)

                git_repo = self.git_service.clone_repository(
                    clone_url=clone_url, target_path=target_path, branch=branch
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
            repo_obj.status = "ready"

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
        self, db: AsyncSession, repository_id: int
    ) -> Optional[Repository]:
        """Retrieves a single repository by ID."""
        return await db.get(Repository, repository_id)

    async def list_repositories(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Repository]:
        """Lists registered repositories."""
        stmt = select(Repository).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_repository(
        self, db: AsyncSession, repository_id: int
    ) -> Optional[Repository]:
        """Deletes a repository record and its local clone folder."""
        repo_obj = await self.get_repository(db, repository_id)
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
