"""Add foreign key indexes

Revision ID: add_fk_indexes
Revises: 43764f29fde7
Create Date: 2026-07-30 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_fk_indexes'
down_revision: Union[str, Sequence[str], None] = '43764f29fde7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_repositories_owner_id', 'repositories', ['owner_id'], unique=False)
    op.create_index('idx_symbols_repository_id', 'symbols', ['repository_id'], unique=False)
    op.create_index('idx_dependency_edges_repository_id', 'dependency_edges', ['repository_id'], unique=False)
    op.create_index('idx_code_chunks_repository_id', 'code_chunks', ['repository_id'], unique=False)
    op.create_index('idx_analysis_runs_repository_id', 'analysis_runs', ['repository_id'], unique=False)
    op.create_index('idx_evaluation_runs_repository_id', 'evaluation_runs', ['repository_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_evaluation_runs_repository_id', table_name='evaluation_runs')
    op.drop_index('idx_analysis_runs_repository_id', table_name='analysis_runs')
    op.drop_index('idx_code_chunks_repository_id', table_name='code_chunks')
    op.drop_index('idx_dependency_edges_repository_id', table_name='dependency_edges')
    op.drop_index('idx_symbols_repository_id', table_name='symbols')
    op.drop_index('idx_repositories_owner_id', table_name='repositories')
