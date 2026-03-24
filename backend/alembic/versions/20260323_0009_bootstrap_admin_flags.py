"""add bootstrap admin flags to users

Revision ID: 20260323_0009
Revises: 20260320_0008
Create Date: 2026-03-23 20:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260323_0009'
down_revision: Union[str, Sequence[str], None] = '20260320_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('must_change_credentials', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'users',
        sa.Column('is_bootstrap_admin', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_bootstrap_admin')
    op.drop_column('users', 'must_change_credentials')
