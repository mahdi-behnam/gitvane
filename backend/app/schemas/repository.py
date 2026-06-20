from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RepositoryCreate(BaseModel):
    """Request schema to register a new repository"""

    name: str = Field(..., description="The name of the repository")
    clone_url: Optional[str] = Field(None, description="The remote clone URL")
    branch: Optional[str] = Field(
        None, description="Optional branch name to clone or inspect"
    )
    local_path: Optional[str] = Field(
        None, description="Optional local workspace folder path"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_clone_or_local(cls, data: Any) -> Any:
        """Validates that either clone_url or local_path (or both) are provided."""
        if isinstance(data, dict):
            clone_url = data.get("clone_url")
            local_path = data.get("local_path")
            if not clone_url and not local_path:
                raise ValueError("Must provide either 'clone_url' or 'local_path'")
        return data


class RepositoryOut(BaseModel):
    """Response schema containing repository details"""

    model_config = ConfigDict(from_attributes=True)

    id: int
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
    repo_metadata: Optional[dict[str, Any]] = Field(None, alias="metadata")
