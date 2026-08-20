"""Add api_keys table for personal API key authentication

Revision ID: add_api_keys_table
Revises: add_perf_and_vector_indexes
Create Date: 2026-08-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_api_keys_table'
down_revision: Union[str, Sequence[str], None] = 'add_perf_and_vector_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_keys table and its indexes."""
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('hashed_key', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hashed_key', name='uq_api_keys_hashed_key')
    )
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'], unique=False)
    op.create_index('idx_api_keys_hashed_key', 'api_keys', ['hashed_key'], unique=False)
    op.create_index(
        'idx_api_keys_active',
        'api_keys',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text('is_revoked = false')
    )


def downgrade() -> None:
    """Drop api_keys table and its indexes."""
    op.drop_index('idx_api_keys_active', table_name='api_keys')
    op.drop_index('idx_api_keys_hashed_key', table_name='api_keys')
    op.drop_index('idx_api_keys_user_id', table_name='api_keys')
    op.drop_table('api_keys')
