"""initial_uuid_schema

Revision ID: 43764f29fde7
Revises: 
Create Date: 2026-07-30 15:57:21.110276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = '43764f29fde7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('oauth_provider', sa.String(), nullable=True),
        sa.Column('oauth_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table(
        'user_refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_refresh_tokens_token'), 'user_refresh_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_user_refresh_tokens_user_id'), 'user_refresh_tokens', ['user_id'], unique=False)

    op.create_table(
        'repositories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('clone_url', sa.String(), nullable=False),
        sa.Column('local_path', sa.String(), nullable=True),
        sa.Column('default_branch', sa.String(), nullable=True),
        sa.Column('current_ref', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('last_indexed_commit', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_pat', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'commits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('sha', sa.String(), nullable=False),
        sa.Column('parent_sha', sa.String(), nullable=True),
        sa.Column('author_name', sa.String(), nullable=True),
        sa.Column('author_email', sa.String(), nullable=True),
        sa.Column('author_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('changed_files', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('insertions', sa.Integer(), nullable=True),
        sa.Column('deletions', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'sha', name='uq_commits_repository_sha')
    )

    op.create_table(
        'code_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('loc', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_test', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_seen_commit', sa.String(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'path', name='uq_code_files_repository_path')
    )

    op.create_table(
        'symbols',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('qualified_name', sa.String(), nullable=False),
        sa.Column('simple_name', sa.String(), nullable=False),
        sa.Column('symbol_type', sa.String(), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('docstring', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_symbols_file_id', 'symbols', ['file_id'], unique=False)
    op.create_index('idx_symbols_lookup', 'symbols', ['repository_id', 'file_id', 'qualified_name', 'start_line'], unique=True)

    op.create_table(
        'dependency_edges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('source_file_id', sa.Integer(), nullable=False),
        sa.Column('target_file_id', sa.Integer(), nullable=False),
        sa.Column('source_symbol_id', sa.Integer(), nullable=True),
        sa.Column('target_symbol_id', sa.Integer(), nullable=True),
        sa.Column('edge_type', sa.String(), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=False, server_default='1.0'),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_symbol_id'], ['symbols.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_symbol_id'], ['symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dependency_edges_source_file_id', 'dependency_edges', ['source_file_id'], unique=False)
    op.create_index('idx_dependency_edges_target_file_id', 'dependency_edges', ['target_file_id'], unique=False)

    op.create_table(
        'code_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=True),
        sa.Column('chunk_type', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('token_count_estimate', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_code_chunks_file_id', 'code_chunks', ['file_id'], unique=False)

    op.create_table(
        'code_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('dimensions', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(settings.EMBEDDING_DIM), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chunk_id'], ['code_chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_code_embeddings_chunk_id', 'code_embeddings', ['chunk_id'], unique=False)

    op.create_table(
        'analysis_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('base_ref', sa.String(), nullable=True),
        sa.Column('head_ref', sa.String(), nullable=True),
        sa.Column('input_mode', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('changed_files', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_symbols', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'impact_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analysis_run_id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('dependency_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0'),
        sa.Column('semantic_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0'),
        sa.Column('cochange_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0'),
        sa.Column('test_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0'),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0'),
        sa.Column('reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommended_tests', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['analysis_run_id'], ['analysis_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['code_files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('base_method', sa.String(), nullable=False),
        sa.Column('commit_limit', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evaluation_run_id', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(), nullable=False),
        sa.Column('scenario', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('predictions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ground_truth', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('evaluation_results')
    op.drop_table('evaluation_runs')
    op.drop_table('impact_predictions')
    op.drop_table('analysis_runs')
    op.drop_table('code_embeddings')
    op.drop_table('code_chunks')
    op.drop_table('dependency_edges')
    op.drop_table('symbols')
    op.drop_table('code_files')
    op.drop_table('commits')
    op.drop_table('repositories')
    op.drop_table('user_refresh_tokens')
    op.drop_table('users')
