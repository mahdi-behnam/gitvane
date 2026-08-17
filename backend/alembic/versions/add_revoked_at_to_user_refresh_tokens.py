"""Add revoked_at column to user_refresh_tokens

Revision ID: add_revoked_at
Revises: decoupled_outbox_schema
Create Date: 2026-08-16 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_revoked_at'
down_revision: Union[str, Sequence[str], None] = 'decoupled_outbox_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'user_refresh_tokens',
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_refresh_tokens', 'revoked_at')
