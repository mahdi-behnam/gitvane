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
    pipeline_version: str | None = Field(None, description="Optional pipeline version override.")
    parser_version: str | None = Field(None, description="Optional parser version override.")
    chunker_version: str | None = Field(None, description="Optional chunker version override.")
    embedding_backend: str | None = Field(None, description="Optional embedding backend override.")
    embedding_model: str | None = Field(None, description="Optional embedding model override.")
    embedding_dimension: int | None = Field(None, description="Optional embedding dimension override.")


class IndexRepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repository_id: UUID
    generation_id: UUID
    status: str
    current_ref: str | None = None
    indexed_at: datetime | None = None
    files_indexed: int = 0
    files_skipped: int = 0
    symbols_indexed: int = 0
    chunks_indexed: int = 0
    embeddings_indexed: int = 0
    dependency_edges_indexed: int = 0
    commits_indexed: int = 0
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

