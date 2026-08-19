from datetime import datetime
from typing import Any, Optional
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    UUID,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    oauth_provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    oauth_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index(
            "idx_users_oauth_provider_id",
            "oauth_provider",
            "oauth_id",
            postgresql_where=text("oauth_provider IS NOT NULL AND oauth_id IS NOT NULL"),
        ),
    )

    # Relationships
    repositories = relationship(
        "Repository", back_populates="owner", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "UserRefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class UserRefreshToken(Base):
    __tablename__ = "user_refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Constraints & Indices
    __table_args__ = (
        Index(
            "idx_user_refresh_tokens_active",
            "user_id",
            postgresql_where=text("is_revoked = false"),
        ),
    )

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    clone_url: Mapped[str] = mapped_column(String, nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    last_indexed_commit: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    active_generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "index_generations.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_repositories_active_generation_id",
        ),
        nullable=True,
    )
    desired_generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "index_generations.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_repositories_desired_generation_id",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    repo_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    encrypted_pat: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Constraints & Indices
    __table_args__ = (
        Index("idx_repositories_owner_id", "owner_id"),
        Index("idx_repositories_owner_created", "owner_id", text("created_at DESC")),
        Index("idx_repositories_active_gen", "active_generation_id"),
        Index("idx_repositories_desired_gen", "desired_generation_id"),
    )

    # Relationships
    owner = relationship("User", back_populates="repositories")
    active_generation = relationship(
        "IndexGeneration",
        foreign_keys=[active_generation_id],
        post_update=True,
    )
    desired_generation = relationship(
        "IndexGeneration",
        foreign_keys=[desired_generation_id],
        post_update=True,
    )
    generations = relationship(
        "IndexGeneration",
        foreign_keys="IndexGeneration.repository_id",
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    commits = relationship(
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    code_files = relationship(
        "CodeFile", back_populates="repository", cascade="all, delete-orphan"
    )
    symbols = relationship(
        "Symbol", back_populates="repository", cascade="all, delete-orphan"
    )
    dependency_edges = relationship(
        "DependencyEdge", back_populates="repository", cascade="all, delete-orphan"
    )
    code_chunks = relationship(
        "CodeChunk", back_populates="repository", cascade="all, delete-orphan"
    )
    analysis_runs = relationship(
        "AnalysisRun", back_populates="repository", cascade="all, delete-orphan"
    )
    evaluation_runs = relationship(
        "EvaluationRun", back_populates="repository", cascade="all, delete-orphan"
    )


class IndexGeneration(Base):
    __tablename__ = "index_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    requested_ref: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pipeline_version: Mapped[str] = mapped_column(Text, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    chunker_version: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_backend: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_config_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    stage_lease_owner: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stage_lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stage_attempt: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    terminal_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cleaned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_index_generations_repo_status", "repository_id", "status"),
        Index("idx_index_generations_status_lease", "status", "stage_lease_expires_at"),
        Index(
            "idx_index_generations_gc",
            "status",
            "terminal_at",
            postgresql_where=text("cleaned_at IS NULL"),
        ),
        Index(
            "idx_index_generations_finalizing_stuck",
            "updated_at",
            postgresql_where=text("status = 'finalizing'"),
        ),
        CheckConstraint(
            "status IN ('queued', 'preparing', 'parsing', 'embedding', 'finalizing', 'completed', 'failed', 'cancelled', 'superseded')",
            name="ck_index_generations_status",
        ),
    )

    # Relationships
    repository = relationship(
        "Repository", foreign_keys=[repository_id], back_populates="generations"
    )
    embedding_batches = relationship(
        "EmbeddingBatch", back_populates="generation", cascade="all, delete-orphan"
    )
    code_files = relationship(
        "CodeFile", back_populates="generation", cascade="all, delete-orphan"
    )
    symbols = relationship(
        "Symbol", back_populates="generation", cascade="all, delete-orphan"
    )
    dependency_edges = relationship(
        "DependencyEdge", back_populates="generation", cascade="all, delete-orphan"
    )
    code_chunks = relationship(
        "CodeChunk", back_populates="generation", cascade="all, delete-orphan"
    )
    code_embeddings = relationship(
        "CodeEmbedding", back_populates="generation", cascade="all, delete-orphan"
    )


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    sha: Mapped[str] = mapped_column(String, nullable=False)
    parent_sha: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_files: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    insertions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deletions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        UniqueConstraint("repository_id", "sha", name="uq_commits_repository_sha"),
        Index("idx_commits_repo_author_date", "repository_id", text("author_date DESC")),
    )

    # Relationships
    repository = relationship("Repository", back_populates="commits")


class CodeFile(Base):
    __tablename__ = "code_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=True
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    loc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_test: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_seen_commit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_code_files_repository_id", "repository_id"),
        Index("idx_code_files_generation_id", "generation_id"),
        Index("idx_code_files_gen_lang", "generation_id", "language"),
        Index("idx_code_files_path_trgm", "path", postgresql_using="gin", postgresql_ops={"path": "gin_trgm_ops"}),
        UniqueConstraint("generation_id", "path", name="uq_code_files_generation_path"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="code_files")
    generation = relationship("IndexGeneration", back_populates="code_files")
    symbols = relationship(
        "Symbol", back_populates="code_file", cascade="all, delete-orphan"
    )
    code_chunks = relationship(
        "CodeChunk", back_populates="code_file", cascade="all, delete-orphan"
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=True
    )
    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False
    )
    qualified_name: Mapped[str] = mapped_column(String, nullable=False)
    simple_name: Mapped[str] = mapped_column(String, nullable=False)
    symbol_type: Mapped[str] = mapped_column(String, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    symbol_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Constraints & Indices
    __table_args__ = (
        Index(
            "idx_symbols_lookup",
            "repository_id",
            "file_id",
            "qualified_name",
            "start_line",
            unique=True,
        ),
        Index("idx_symbols_repository_id", "repository_id"),
        Index("idx_symbols_generation_id", "generation_id"),
        Index("idx_symbols_file_id", "file_id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="symbols")
    generation = relationship("IndexGeneration", back_populates="symbols")
    code_file = relationship("CodeFile", back_populates="symbols")
    code_chunks = relationship(
        "CodeChunk", back_populates="symbol", cascade="all, delete-orphan"
    )


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=True
    )
    source_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False
    )
    target_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False
    )
    source_symbol_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True
    )
    target_symbol_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True
    )
    edge_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=1.0, nullable=False
    )
    evidence: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_dependency_edges_repository_id", "repository_id"),
        Index("idx_dependency_edges_generation_id", "generation_id"),
        Index("idx_dependency_edges_source_file_id", "source_file_id"),
        Index("idx_dependency_edges_target_file_id", "target_file_id"),
        Index("idx_dependency_edges_gen_source", "generation_id", "source_file_id"),
        Index("idx_dependency_edges_gen_target", "generation_id", "target_file_id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="dependency_edges")
    generation = relationship("IndexGeneration", back_populates="dependency_edges")
    source_file = relationship("CodeFile", foreign_keys=[source_file_id])
    target_file = relationship("CodeFile", foreign_keys=[target_file_id])
    source_symbol = relationship("Symbol", foreign_keys=[source_symbol_id])
    target_symbol = relationship("Symbol", foreign_keys=[target_symbol_id])


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=True
    )
    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False
    )
    symbol_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("symbols.id", ondelete="SET NULL"), nullable=True
    )
    chunk_type: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    token_count_estimate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_code_chunks_repository_id", "repository_id"),
        Index("idx_code_chunks_generation_id", "generation_id"),
        Index("idx_code_chunks_file_id", "file_id"),
        Index("idx_code_chunks_gen_id_range", "generation_id", "id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="code_chunks")
    generation = relationship("IndexGeneration", back_populates="code_chunks")
    code_file = relationship("CodeFile", back_populates="code_chunks")
    symbol = relationship("Symbol", back_populates="code_chunks")
    embedding = relationship(
        "CodeEmbedding", back_populates="code_chunk", cascade="all, delete-orphan"
    )


class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=True
    )
    chunk_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_chunks.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_code_embeddings_chunk_id", "chunk_id"),
        Index("idx_code_embeddings_generation_id", "generation_id"),
        Index(
            "idx_code_embeddings_vector_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint("generation_id", "chunk_id", "model", name="uq_code_embeddings_gen_chunk_model"),
    )

    # Relationships
    generation = relationship("IndexGeneration", back_populates="code_embeddings")
    code_chunk = relationship("CodeChunk", back_populates="embedding")


class EmbeddingBatch(Base):
    __tablename__ = "embedding_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("index_generations.id", ondelete="CASCADE"), nullable=False
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    chunk_start_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_end_id: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_owner: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("generation_id", "batch_index", name="uq_embedding_batches_gen_index"),
        Index("idx_embedding_batches_gen_status", "generation_id", "status"),
        Index("idx_embedding_batches_status_lease", "status", "lease_expires_at"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_embedding_batches_status",
        ),
    )

    # Relationships
    generation = relationship("IndexGeneration", back_populates="embedding_batches")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_outbox_events_pending",
            "next_attempt_at",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "idx_outbox_events_processing_lease",
            "locked_at",
            postgresql_where=text("status = 'processing'"),
        ),
        Index(
            "idx_outbox_events_active_aggregate",
            "aggregate_id",
            "event_type",
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'published', 'failed')",
            name="ck_outbox_events_status",
        ),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    base_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    head_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    changed_files: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    changed_symbols: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Constraints & Indices
    __table_args__ = (
        Index("idx_analysis_runs_repository_id", "repository_id"),
        Index("idx_analysis_runs_repo_started", "repository_id", text("started_at DESC")),
    )

    # Relationships
    repository = relationship("Repository", back_populates="analysis_runs")
    predictions = relationship(
        "ImpactPrediction",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )


class ImpactPrediction(Base):
    __tablename__ = "impact_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(precision=5, scale=4), nullable=False)
    dependency_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=0.0, nullable=False
    )
    semantic_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=0.0, nullable=False
    )
    cochange_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=0.0, nullable=False
    )
    test_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=0.0, nullable=False
    )
    risk_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), default=0.0, nullable=False
    )
    reasons: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    recommended_tests: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)

    # Constraints & Indices
    __table_args__ = (
        Index("idx_impact_predictions_run_rank", "analysis_run_id", "rank"),
        Index("idx_impact_predictions_file_id", "file_id"),
    )

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="predictions")
    code_file = relationship("CodeFile")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    base_method: Mapped[str] = mapped_column(String, nullable=False)
    commit_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Constraints & Indices
    __table_args__ = (
        Index("idx_evaluation_runs_repository_id", "repository_id"),
        Index("idx_evaluation_runs_repo_started", "repository_id", text("started_at DESC")),
    )

    # Relationships
    repository = relationship("Repository", back_populates="evaluation_runs")
    results = relationship(
        "EvaluationResult",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String, nullable=False)
    scenario: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    predictions: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    ground_truth: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_evaluation_results_run_id", "evaluation_run_id", "id"),
    )

    # Relationships
    evaluation_run = relationship("EvaluationRun", back_populates="results")
