from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    clone_url: Mapped[str] = mapped_column(String, nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    last_indexed_commit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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

    # Relationships
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


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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
    )

    # Relationships
    repository = relationship("Repository", back_populates="commits")


class CodeFile(Base):
    __tablename__ = "code_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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

    # Constraints
    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_code_files_repository_path"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="code_files")
    symbols = relationship(
        "Symbol", back_populates="code_file", cascade="all, delete-orphan"
    )
    code_chunks = relationship(
        "CodeChunk", back_populates="code_file", cascade="all, delete-orphan"
    )


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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
        Index("idx_symbols_file_id", "file_id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="symbols")
    code_file = relationship("CodeFile", back_populates="symbols")
    code_chunks = relationship(
        "CodeChunk", back_populates="symbol", cascade="all, delete-orphan"
    )


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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
        Index("idx_dependency_edges_source_file_id", "source_file_id"),
        Index("idx_dependency_edges_target_file_id", "target_file_id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="dependency_edges")
    source_file = relationship("CodeFile", foreign_keys=[source_file_id])
    target_file = relationship("CodeFile", foreign_keys=[target_file_id])
    source_symbol = relationship("Symbol", foreign_keys=[source_symbol_id])
    target_symbol = relationship("Symbol", foreign_keys=[target_symbol_id])


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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
        Index("idx_code_chunks_file_id", "file_id"),
    )

    # Relationships
    repository = relationship("Repository", back_populates="code_chunks")
    code_file = relationship("CodeFile", back_populates="code_chunks")
    symbol = relationship("Symbol", back_populates="code_chunks")
    embedding = relationship(
        "CodeEmbedding", back_populates="code_chunk", cascade="all, delete-orphan"
    )


class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("code_chunks.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Constraints & Indices
    __table_args__ = (
        Index("idx_code_embeddings_chunk_id", "chunk_id"),
    )

    # Relationships
    code_chunk = relationship("CodeChunk", back_populates="embedding")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="predictions")
    code_file = relationship("CodeFile")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
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

    # Relationships
    evaluation_run = relationship("EvaluationRun", back_populates="results")
