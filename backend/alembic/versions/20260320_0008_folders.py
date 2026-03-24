"""add global folders taxonomy for documents

Revision ID: 20260320_0008
Revises: 20260319_0007
Create Date: 2026-03-20 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260320_0008'
down_revision: Union[str, Sequence[str], None] = '20260319_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_folders_id', 'folders', ['id'], unique=False)
    op.create_index('ix_folders_name', 'folders', ['name'], unique=True)

    op.add_column('documents', sa.Column('folder_id', sa.Integer(), nullable=True))
    op.create_index('ix_documents_folder_id', 'documents', ['folder_id'], unique=False)
    op.create_foreign_key(
        'documents_folder_id_fkey',
        'documents',
        'folders',
        ['folder_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('documents_folder_id_fkey', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_folder_id', table_name='documents')
    op.drop_column('documents', 'folder_id')

    op.drop_index('ix_folders_name', table_name='folders')
    op.drop_index('ix_folders_id', table_name='folders')
    op.drop_table('folders')
