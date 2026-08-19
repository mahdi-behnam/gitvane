from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepositoryCreate(BaseModel):
    """Request schema to register a new repository"""

    name: str = Field(..., min_length=1, description="The name of the repository")
    clone_url: str = Field(..., min_length=1, description="The remote clone URL")
    branch: str = Field(
        ..., min_length=1, description="Branch name to clone or inspect"
    )
    index_now: bool = Field(
        True,
        description=(
            "When true, trigger indexing immediately after the repository is "
            "registered. Requires the indexing pipeline to be active."
        ),
    )
    pat: Optional[str] = Field(
        None,
        description="Optional Personal Access Token for authenticating clone/fetch",
    )

    @field_validator("name", "clone_url", "branch")
    @classmethod
    def validate_non_empty(cls, v: str, info: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty or whitespace")
        return v.strip()


class RepositorySyncRequest(BaseModel):
    """Request schema to sync remote changes and re-index a repository"""

    branch: Optional[str] = Field(
        None,
        description=(
            "Optional branch or ref to pull and checkout before re-indexing. "
            "If omitted, uses the repository default branch or current ref."
        ),
    )


class RemoteBranchesRequest(BaseModel):
    """Request schema to inspect available remote branches for a repository URL"""

    clone_url: str = Field(..., min_length=1, description="The remote clone URL")
    pat: Optional[str] = Field(
        None,
        description="Optional Personal Access Token for authenticating remote lookup",
    )

    @field_validator("clone_url")
    @classmethod
    def validate_clone_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("clone_url must not be empty or whitespace")
        return v.strip()


class RemoteBranchesResponse(BaseModel):
    """Response schema containing list of remote branches and optional default branch"""

    branches: list["RefSearchResult"]
    default_branch: Optional[str] = None


class RepositoryOut(BaseModel):
    """Response schema containing repository details"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    clone_url: Optional[str] = None
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


