"""add chat message sources

Revision ID: 20260303_0002
Revises: 20260303_0001
Create Date: 2026-03-03 22:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260303_0002'
down_revision: Union[str, Sequence[str], None] = '20260303_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_message_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('source_order', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('chunk_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('csv_row_start', sa.Integer(), nullable=True),
        sa.Column('csv_row_end', sa.Integer(), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_message_sources_id', 'chat_message_sources', ['id'], unique=False)
    op.create_index('ix_chat_message_sources_message_id', 'chat_message_sources', ['message_id'], unique=False)
    op.create_index('ix_chat_message_sources_document_id', 'chat_message_sources', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chat_message_sources_document_id', table_name='chat_message_sources')
    op.drop_index('ix_chat_message_sources_message_id', table_name='chat_message_sources')
    op.drop_index('ix_chat_message_sources_id', table_name='chat_message_sources')
    op.drop_table('chat_message_sources')
