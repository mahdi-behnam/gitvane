from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IndexingBase(BaseModel):
    repository_id: UUID


class IndexRepositoryRequest(BaseModel):
    ref: str | None = Field(
        None,
        description="Optional branch, tag, or commit to checkout before indexing.",
    )


class IndexRepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repository_id: UUID
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


class IndexingProgressEvent(BaseModel):
    repository_id: UUID
    status: str  # "indexing", "indexed", "index_failed"
    phase: str  # "parsing", "saving", "embeddings", "graph_and_commits", "completed"
    phase_name: str
    files_total: int = 0
    files_processed: int = 0
    chunks_total: int = 0
    chunks_processed: int = 0
    progress_percentage: float = 0.0
    estimated_seconds_remaining: int | None = None
    error: str | None = None


class IndexStatusResponse(BaseModel):
    repository_id: UUID
    status: str
    current_ref: str | None = None
    last_indexed_commit: str | None = None
    indexed_at: datetime | None = None
    file_count: int
    symbol_count: int
    chunk_count: int
    dependency_edge_count: int
    commit_count: int
    progress: IndexingProgressEvent | None = None

