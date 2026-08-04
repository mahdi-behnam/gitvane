from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    """Request schema to register a new repository"""

    name: str = Field(..., description="The name of the repository")
    clone_url: str = Field(..., description="The remote clone URL")
    branch: Optional[str] = Field(
        None, description="Optional branch name to clone or inspect"
    )
    index_now: bool = Field(
        False,
        description=(
            "When true, trigger indexing immediately after the repository is "
            "registered. Requires the indexing pipeline to be active."
        ),
    )
    pat: Optional[str] = Field(
        None,
        description="Optional Personal Access Token for authenticating clone/fetch",
    )


class RepositoryOut(BaseModel):
    """Response schema containing repository details"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    clone_url: Optional[str] = None
    local_path: Optional[str] = None
    default_branch: Optional[str] = None
    current_ref: Optional[str] = None
    status: str
    last_indexed_commit: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None
    # The DB model exposes this column as repo_metadata (mapped to the
    # "metadata" DB column to avoid conflict with SQLAlchemy's reserved name).
    repo_metadata: Optional[dict[str, Any]] = Field(None)


class RepositoryList(BaseModel):
    """Response schema for a paginated list of repositories"""

    items: list[RepositoryOut]
    total: int
    skip: int
    limit: int


class FileSearchResult(BaseModel):
    """Response schema for repository file autocomplete search"""

    id: int
    path: str
    language: str
    loc: int
    is_test: bool


class RefSearchResult(BaseModel):
    """Response schema for repository git ref autocomplete search"""

    name: str = Field(..., description="Ref display name (branch, tag, or commit SHA)")
    ref_type: str = Field(..., description="Ref type: 'branch', 'tag', or 'commit'")
    commit_sha: Optional[str] = Field(None, description="Full or short commit SHA")
    commit_message: Optional[str] = Field(None, description="Short commit message summary")
    commit_date: Optional[str] = Field(None, description="Commit timestamp string")


