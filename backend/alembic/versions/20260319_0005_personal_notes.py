"""add personal notes table

Revision ID: 20260319_0005
Revises: 20260319_0004
Create Date: 2026-03-19 14:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260319_0005'
down_revision: Union[str, Sequence[str], None] = '20260319_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'personal_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personal_notes_id', 'personal_notes', ['id'], unique=False)
    op.create_index('ix_personal_notes_user_id', 'personal_notes', ['user_id'], unique=False)
    op.create_index('ix_personal_notes_updated_at', 'personal_notes', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_personal_notes_updated_at', table_name='personal_notes')
    op.drop_index('ix_personal_notes_user_id', table_name='personal_notes')
    op.drop_index('ix_personal_notes_id', table_name='personal_notes')
    op.drop_table('personal_notes')
