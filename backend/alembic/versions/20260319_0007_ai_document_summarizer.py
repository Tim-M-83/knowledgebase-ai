"""add ai document summarizer tables

Revision ID: 20260319_0007
Revises: 20260319_0006
Create Date: 2026-03-19 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20260319_0007'
down_revision: Union[str, Sequence[str], None] = '20260319_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    status_enum = postgresql.ENUM(
        'uploaded',
        'processing',
        'ready',
        'failed',
        name='summarizer_document_status_enum',
        create_type=False,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'summarizer_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=120), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('status', status_enum, nullable=False, server_default=sa.text("'uploaded'")),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('summary_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename'),
    )
    op.create_index('ix_summarizer_documents_id', 'summarizer_documents', ['id'], unique=False)
    op.create_index('ix_summarizer_documents_owner_id', 'summarizer_documents', ['owner_id'], unique=False)
    op.create_index(
        'ix_summarizer_documents_original_name',
        'summarizer_documents',
        ['original_name'],
        unique=False,
    )
    op.create_index('ix_summarizer_documents_status', 'summarizer_documents', ['status'], unique=False)

    op.create_table(
        'summarizer_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['summarizer_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_summarizer_chunks_id', 'summarizer_chunks', ['id'], unique=False)
    op.create_index('ix_summarizer_chunks_document_id', 'summarizer_chunks', ['document_id'], unique=False)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_summarizer_chunks_embedding_ivfflat ON summarizer_chunks '
        'USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)'
    )

    op.create_table(
        'summarizer_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'assistant', 'system', name='chat_role_enum', create_type=False), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['summarizer_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_summarizer_messages_id', 'summarizer_messages', ['id'], unique=False)
    op.create_index('ix_summarizer_messages_document_id', 'summarizer_messages', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_summarizer_messages_document_id', table_name='summarizer_messages')
    op.drop_index('ix_summarizer_messages_id', table_name='summarizer_messages')
    op.drop_table('summarizer_messages')

    op.execute('DROP INDEX IF EXISTS ix_summarizer_chunks_embedding_ivfflat')
    op.drop_index('ix_summarizer_chunks_document_id', table_name='summarizer_chunks')
    op.drop_index('ix_summarizer_chunks_id', table_name='summarizer_chunks')
    op.drop_table('summarizer_chunks')

    op.drop_index('ix_summarizer_documents_status', table_name='summarizer_documents')
    op.drop_index('ix_summarizer_documents_original_name', table_name='summarizer_documents')
    op.drop_index('ix_summarizer_documents_owner_id', table_name='summarizer_documents')
    op.drop_index('ix_summarizer_documents_id', table_name='summarizer_documents')
    op.drop_table('summarizer_documents')

    status_enum = postgresql.ENUM(
        'uploaded',
        'processing',
        'ready',
        'failed',
        name='summarizer_document_status_enum',
        create_type=False,
    )
    status_enum.drop(op.get_bind(), checkfirst=True)
