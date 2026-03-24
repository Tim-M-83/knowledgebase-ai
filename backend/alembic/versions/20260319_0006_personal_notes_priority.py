"""add priority to personal notes

Revision ID: 20260319_0006
Revises: 20260319_0005
Create Date: 2026-03-19 15:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260319_0006'
down_revision: Union[str, Sequence[str], None] = '20260319_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'personal_notes',
        sa.Column('priority', sa.String(length=16), nullable=False, server_default=sa.text("'none'")),
    )
    op.execute("UPDATE personal_notes SET priority = 'none' WHERE priority IS NULL")


def downgrade() -> None:
    op.drop_column('personal_notes', 'priority')
