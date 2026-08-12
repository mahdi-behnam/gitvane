"""Add IndexGeneration, EmbeddingBatch, OutboxEvent tables and generation-scoped schema

Revision ID: decoupled_outbox_schema
Revises: 6ec32e4180bd
Create Date: 2026-08-12 22:55:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'decoupled_outbox_schema'
down_revision: Union[str, Sequence[str], None] = '6ec32e4180bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create IndexGeneration table
    op.create_table(
        'index_generations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('requested_ref', sa.Text(), nullable=False),
        sa.Column('commit_sha', sa.Text(), nullable=True),
        sa.Column('pipeline_version', sa.Text(), nullable=False),
        sa.Column('parser_version', sa.Text(), nullable=False),
        sa.Column('chunker_version', sa.Text(), nullable=False),
        sa.Column('embedding_backend', sa.Text(), nullable=False),
        sa.Column('embedding_model', sa.Text(), nullable=False),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False),
        sa.Column('embedding_config_hash', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('stage_lease_owner', sa.Text(), nullable=True),
        sa.Column('stage_lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stage_attempt', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminal_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'preparing', 'parsing', 'embedding', 'finalizing', 'completed', 'failed', 'cancelled', 'superseded')",
            name='ck_index_generations_status'
        ),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. Create EmbeddingBatch table
    op.create_table(
        'embedding_batches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('generation_id', sa.UUID(), nullable=False),
        sa.Column('batch_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('chunk_start_id', sa.Integer(), nullable=False),
        sa.Column('chunk_end_id', sa.Integer(), nullable=False),
        sa.Column('lease_owner', sa.Text(), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='ck_embedding_batches_status'),
        sa.ForeignKeyConstraint(['generation_id'], ['index_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('generation_id', 'batch_index', name='uq_embedding_batches_gen_index')
    )

    # 3. Create OutboxEvent table
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('aggregate_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'processing', 'published', 'failed')", name='ck_outbox_events_status'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Add active_generation_id / desired_generation_id to repositories as nullable
    op.add_column('repositories', sa.Column('active_generation_id', sa.UUID(), nullable=True))
    op.add_column('repositories', sa.Column('desired_generation_id', sa.UUID(), nullable=True))

    # 5. Add nullable generation_id to graph/vector tables
    op.add_column('code_files', sa.Column('generation_id', sa.UUID(), nullable=True))
    op.add_column('symbols', sa.Column('generation_id', sa.UUID(), nullable=True))
    op.add_column('dependency_edges', sa.Column('generation_id', sa.UUID(), nullable=True))
    op.add_column('code_chunks', sa.Column('generation_id', sa.UUID(), nullable=True))
    op.add_column('code_embeddings', sa.Column('generation_id', sa.UUID(), nullable=True))

    # 6. Legacy generation backfill in bounded batches
    connection = op.get_bind()
    repos = connection.execute(
        sa.text("SELECT id, current_ref, default_branch, last_indexed_commit FROM repositories")
    ).fetchall()

    for repo in repos:
        repo_id = repo[0]
        ref = repo[1] or repo[2] or "HEAD"
        sha = repo[3] or repo[1] or "legacy"
        gen_id = str(uuid.uuid4())

        connection.execute(
            sa.text("""
                INSERT INTO index_generations (
                    id, repository_id, requested_ref, commit_sha,
                    pipeline_version, parser_version, chunker_version,
                    embedding_backend, embedding_model, embedding_dimension, embedding_config_hash,
                    status, created_at, updated_at, completed_at, terminal_at
                ) VALUES (
                    :id, :repo_id, :ref, :sha,
                    'v0.0.0-legacy', 'v0.0.0-legacy', 'v0.0.0-legacy',
                    'legacy', 'legacy', 768, 'legacy',
                    'completed', NOW(), NOW(), NOW(), NOW()
                )
            """),
            {"id": gen_id, "repo_id": str(repo_id), "ref": ref, "sha": sha}
        )

        connection.execute(
            sa.text("""
                UPDATE repositories
                SET active_generation_id = :gen_id, desired_generation_id = :gen_id
                WHERE id = :repo_id
            """),
            {"gen_id": gen_id, "repo_id": str(repo_id)}
        )

        for table_name in ["code_files", "symbols", "dependency_edges", "code_chunks"]:
            while True:
                res = connection.execute(
                    sa.text(f"""
                        UPDATE {table_name}
                        SET generation_id = :gen_id
                        WHERE id IN (
                            SELECT id FROM {table_name}
                            WHERE repository_id = :repo_id AND generation_id IS NULL
                            LIMIT 1000
                        )
                    """),
                    {"gen_id": gen_id, "repo_id": str(repo_id)}
                )
                if res.rowcount == 0:
                    break

        while True:
            res = connection.execute(
                sa.text("""
                    UPDATE code_embeddings
                    SET generation_id = :gen_id
                    WHERE id IN (
                        SELECT ce.id FROM code_embeddings ce
                        JOIN code_chunks cc ON ce.chunk_id = cc.id
                        WHERE cc.repository_id = :repo_id AND ce.generation_id IS NULL
                        LIMIT 1000
                    )
                """),
                {"gen_id": gen_id, "repo_id": str(repo_id)}
            )
            if res.rowcount == 0:
                break

    # 7. Add indexes
    op.create_index('idx_index_generations_repo_status', 'index_generations', ['repository_id', 'status'], unique=False)
    op.create_index('idx_index_generations_status_lease', 'index_generations', ['status', 'stage_lease_expires_at'], unique=False)
    op.create_index('idx_embedding_batches_gen_status', 'embedding_batches', ['generation_id', 'status'], unique=False)
    op.create_index('idx_embedding_batches_status_lease', 'embedding_batches', ['status', 'lease_expires_at'], unique=False)
    op.create_index(
        'idx_outbox_events_pending',
        'outbox_events',
        ['next_attempt_at', 'created_at'],
        unique=False,
        postgresql_where=sa.text("status = 'pending'")
    )

    op.create_index('idx_code_files_generation_id', 'code_files', ['generation_id'], unique=False)
    op.create_index('idx_symbols_generation_id', 'symbols', ['generation_id'], unique=False)
    op.create_index('idx_dependency_edges_generation_id', 'dependency_edges', ['generation_id'], unique=False)
    op.create_index('idx_code_chunks_generation_id', 'code_chunks', ['generation_id'], unique=False)
    op.create_index('idx_code_embeddings_generation_id', 'code_embeddings', ['generation_id'], unique=False)
    op.create_index('idx_repositories_active_gen', 'repositories', ['active_generation_id'], unique=False)
    op.create_index('idx_repositories_desired_gen', 'repositories', ['desired_generation_id'], unique=False)

    # 8. Foreign keys and unique constraints
    try:
        op.drop_constraint('uq_code_files_repository_path', 'code_files', type_='unique')
    except Exception:
        pass

    op.create_unique_constraint('uq_code_files_generation_path', 'code_files', ['generation_id', 'path'])
    op.create_unique_constraint('uq_code_embeddings_gen_chunk_model', 'code_embeddings', ['generation_id', 'chunk_id', 'model'])

    op.create_foreign_key('fk_repositories_active_gen', 'repositories', 'index_generations', ['active_generation_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_repositories_desired_gen', 'repositories', 'index_generations', ['desired_generation_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_code_files_generation', 'code_files', 'index_generations', ['generation_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_symbols_generation', 'symbols', 'index_generations', ['generation_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_dependency_edges_generation', 'dependency_edges', 'index_generations', ['generation_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_code_chunks_generation', 'code_chunks', 'index_generations', ['generation_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_code_embeddings_generation', 'code_embeddings', 'index_generations', ['generation_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('fk_code_embeddings_generation', 'code_embeddings', type_='foreignkey')
    op.drop_constraint('fk_code_chunks_generation', 'code_chunks', type_='foreignkey')
    op.drop_constraint('fk_dependency_edges_generation', 'dependency_edges', type_='foreignkey')
    op.drop_constraint('fk_symbols_generation', 'symbols', type_='foreignkey')
    op.drop_constraint('fk_code_files_generation', 'code_files', type_='foreignkey')
    op.drop_constraint('fk_repositories_desired_gen', 'repositories', type_='foreignkey')
    op.drop_constraint('fk_repositories_active_gen', 'repositories', type_='foreignkey')

    op.drop_constraint('uq_code_embeddings_gen_chunk_model', 'code_embeddings', type_='unique')
    op.drop_constraint('uq_code_files_generation_path', 'code_files', type_='unique')

    op.create_unique_constraint('uq_code_files_repository_path', 'code_files', ['repository_id', 'path'])

    op.drop_index('idx_repositories_desired_gen', table_name='repositories')
    op.drop_index('idx_repositories_active_gen', table_name='repositories')
    op.drop_index('idx_code_embeddings_generation_id', table_name='code_embeddings')
    op.drop_index('idx_code_chunks_generation_id', table_name='code_chunks')
    op.drop_index('idx_dependency_edges_generation_id', table_name='dependency_edges')
    op.drop_index('idx_symbols_generation_id', table_name='symbols')
    op.drop_index('idx_code_files_generation_id', table_name='code_files')
    op.drop_index('idx_outbox_events_pending', table_name='outbox_events')
    op.drop_index('idx_embedding_batches_status_lease', table_name='embedding_batches')
    op.drop_index('idx_embedding_batches_gen_status', table_name='embedding_batches')
    op.drop_index('idx_index_generations_status_lease', table_name='index_generations')
    op.drop_index('idx_index_generations_repo_status', table_name='index_generations')

    op.drop_column('code_embeddings', 'generation_id')
    op.drop_column('code_chunks', 'generation_id')
    op.drop_column('dependency_edges', 'generation_id')
    op.drop_column('symbols', 'generation_id')
    op.drop_column('code_files', 'generation_id')
    op.drop_column('repositories', 'desired_generation_id')
    op.drop_column('repositories', 'active_generation_id')

    op.drop_table('outbox_events')
    op.drop_table('embedding_batches')
    op.drop_table('index_generations')
