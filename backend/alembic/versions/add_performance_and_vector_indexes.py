"""Add performance, vector, trigram, and composite indexes

Revision ID: add_perf_and_vector_indexes
Revises: add_revoked_at
Create Date: 2026-08-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_perf_and_vector_indexes'
down_revision: Union[str, Sequence[str], None] = 'add_revoked_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema with performance indexes."""
    # 1. Enable pg_trgm extension for fast ILIKE / substring searches
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Vector index for semantic search
    op.create_index(
        'idx_code_embeddings_vector_hnsw',
        'code_embeddings',
        ['embedding'],
        unique=False,
        postgresql_using='hnsw',
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )

    # 3. Code files indexes
    op.create_index(
        'idx_code_files_repository_id',
        'code_files',
        ['repository_id'],
        unique=False,
    )
    op.create_index(
        'idx_code_files_gen_lang',
        'code_files',
        ['generation_id', 'language'],
        unique=False,
    )
    op.create_index(
        'idx_code_files_path_trgm',
        'code_files',
        ['path'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'path': 'gin_trgm_ops'},
    )

    # 4. Dependency edges composite indexes
    op.create_index(
        'idx_dependency_edges_gen_source',
        'dependency_edges',
        ['generation_id', 'source_file_id'],
        unique=False,
    )
    op.create_index(
        'idx_dependency_edges_gen_target',
        'dependency_edges',
        ['generation_id', 'target_file_id'],
        unique=False,
    )

    # 5. Code chunks batch ID range index
    op.create_index(
        'idx_code_chunks_gen_id_range',
        'code_chunks',
        ['generation_id', 'id'],
        unique=False,
    )

    # 6. Impact predictions indexes
    op.create_index(
        'idx_impact_predictions_run_rank',
        'impact_predictions',
        ['analysis_run_id', 'rank'],
        unique=False,
    )
    op.create_index(
        'idx_impact_predictions_file_id',
        'impact_predictions',
        ['file_id'],
        unique=False,
    )

    # 7. Evaluation results index
    op.create_index(
        'idx_evaluation_results_run_id',
        'evaluation_results',
        ['evaluation_run_id', 'id'],
        unique=False,
    )

    # 8. Outbox events reconciler partial indexes
    op.create_index(
        'idx_outbox_events_processing_lease',
        'outbox_events',
        ['locked_at'],
        unique=False,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.create_index(
        'idx_outbox_events_active_aggregate',
        'outbox_events',
        ['aggregate_id', 'event_type'],
        unique=False,
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )

    # 9. Index generations GC and reconciler partial indexes
    op.create_index(
        'idx_index_generations_gc',
        'index_generations',
        ['status', 'terminal_at'],
        unique=False,
        postgresql_where=sa.text("cleaned_at IS NULL"),
    )
    op.create_index(
        'idx_index_generations_finalizing_stuck',
        'index_generations',
        ['updated_at'],
        unique=False,
        postgresql_where=sa.text("status = 'finalizing'"),
    )

    # 10. Repository, Commit, Run listing pagination composite indexes
    op.create_index(
        'idx_repositories_owner_created',
        'repositories',
        ['owner_id', sa.text('created_at DESC')],
        unique=False,
    )
    op.create_index(
        'idx_commits_repo_author_date',
        'commits',
        ['repository_id', sa.text('author_date DESC NULLS LAST')],
        unique=False,
    )
    op.create_index(
        'idx_analysis_runs_repo_started',
        'analysis_runs',
        ['repository_id', sa.text('started_at DESC')],
        unique=False,
    )
    op.create_index(
        'idx_evaluation_runs_repo_started',
        'evaluation_runs',
        ['repository_id', sa.text('started_at DESC')],
        unique=False,
    )

    # 11. User and Refresh token auth indexes
    op.create_index(
        'idx_users_oauth_provider_id',
        'users',
        ['oauth_provider', 'oauth_id'],
        unique=True,
        postgresql_where=sa.text("oauth_provider IS NOT NULL AND oauth_id IS NOT NULL"),
    )
    op.create_index(
        'idx_user_refresh_tokens_active',
        'user_refresh_tokens',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text("is_revoked = false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_user_refresh_tokens_active', table_name='user_refresh_tokens')
    op.drop_index('idx_users_oauth_provider_id', table_name='users')
    op.drop_index('idx_evaluation_runs_repo_started', table_name='evaluation_runs')
    op.drop_index('idx_analysis_runs_repo_started', table_name='analysis_runs')
    op.drop_index('idx_commits_repo_author_date', table_name='commits')
    op.drop_index('idx_repositories_owner_created', table_name='repositories')
    op.drop_index('idx_index_generations_finalizing_stuck', table_name='index_generations')
    op.drop_index('idx_index_generations_gc', table_name='index_generations')
    op.drop_index('idx_outbox_events_active_aggregate', table_name='outbox_events')
    op.drop_index('idx_outbox_events_processing_lease', table_name='outbox_events')
    op.drop_index('idx_evaluation_results_run_id', table_name='evaluation_results')
    op.drop_index('idx_impact_predictions_file_id', table_name='impact_predictions')
    op.drop_index('idx_impact_predictions_run_rank', table_name='impact_predictions')
    op.drop_index('idx_code_chunks_gen_id_range', table_name='code_chunks')
    op.drop_index('idx_dependency_edges_gen_target', table_name='dependency_edges')
    op.drop_index('idx_dependency_edges_gen_source', table_name='dependency_edges')
    op.drop_index('idx_code_files_path_trgm', table_name='code_files')
    op.drop_index('idx_code_files_gen_lang', table_name='code_files')
    op.drop_index('idx_code_files_repository_id', table_name='code_files')
    op.drop_index('idx_code_embeddings_vector_hnsw', table_name='code_embeddings')
