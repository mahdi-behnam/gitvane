from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IndexingBase(BaseModel):
    repository_id: int


class IndexRepositoryRequest(BaseModel):
    ref: str | None = Field(
        None,
        description="Optional branch, tag, or commit to checkout before indexing.",
    )


class IndexRepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repository_id: int
    status: str
    current_ref: str | None = None
    indexed_at: datetime | None = None
    files_indexed: int
    files_skipped: int
    symbols_indexed: int
    chunks_indexed: int
    embeddings_indexed: int = 0
    dependency_edges_indexed: int
    commits_indexed: int
    parser_errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IndexStatusResponse(BaseModel):
    repository_id: int
    status: str
    current_ref: str | None = None
    last_indexed_commit: str | None = None
    indexed_at: datetime | None = None
    file_count: int
    symbol_count: int
    chunk_count: int
    dependency_edge_count: int
    commit_count: int
