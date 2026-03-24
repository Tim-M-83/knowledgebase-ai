"""init schema

Revision ID: 20260303_0001
Revises:
Create Date: 2026-03-03 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = '20260303_0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    role_enum = postgresql.ENUM('admin', 'editor', 'viewer', name='role_enum', create_type=False)
    role_enum.create(op.get_bind(), checkfirst=True)

    visibility_enum = postgresql.ENUM('company', 'department', 'private', name='document_visibility_enum', create_type=False)
    visibility_enum.create(op.get_bind(), checkfirst=True)

    doc_status_enum = postgresql.ENUM('uploaded', 'processing', 'ready', 'failed', name='document_status_enum', create_type=False)
    doc_status_enum.create(op.get_bind(), checkfirst=True)

    chat_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='chat_role_enum', create_type=False)
    chat_role_enum.create(op.get_bind(), checkfirst=True)

    feedback_rating_enum = postgresql.ENUM('up', 'down', name='feedback_rating_enum', create_type=False)
    feedback_rating_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_app_settings_key', 'app_settings', ['key'], unique=True)

    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_departments_id', 'departments', ['id'], unique=False)
    op.create_index('ix_departments_name', 'departments', ['name'], unique=True)

    op.create_table(
        'tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tags_id', 'tags', ['id'], unique=False)
    op.create_index('ix_tags_name', 'tags', ['name'], unique=True)

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', role_enum, nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=120), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('visibility', visibility_enum, nullable=False),
        sa.Column('status', doc_status_enum, nullable=False),
        sa.Column('error_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename'),
    )
    op.create_index('ix_documents_id', 'documents', ['id'], unique=False)
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'], unique=False)
    op.create_index('ix_documents_original_name', 'documents', ['original_name'], unique=False)

    op.create_table(
        'document_tags',
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'tag_id'),
        sa.UniqueConstraint('document_id', 'tag_id', name='uq_document_tag'),
    )
    op.create_index('ix_document_tags_tag_id', 'document_tags', ['tag_id'], unique=False)

    op.create_table(
        'chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chunks_id', 'chunks', ['id'], unique=False)
    op.create_index('ix_chunks_document_id', 'chunks', ['document_id'], unique=False)
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat ON chunks '
        'USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)'
    )

    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_sessions_id', 'chat_sessions', ['id'], unique=False)
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', chat_role_enum, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'], unique=False)

    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('rating', feedback_rating_enum, nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feedback_id', 'feedback', ['id'], unique=False)
    op.create_index('ix_feedback_message_id', 'feedback', ['message_id'], unique=False)

    op.create_table(
        'retrieval_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('top_k', sa.Integer(), nullable=False),
        sa.Column('avg_score', sa.Float(), nullable=False),
        sa.Column('had_sources', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('low_confidence', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_retrieval_logs_id', 'retrieval_logs', ['id'], unique=False)
    op.create_index('ix_retrieval_logs_session_id', 'retrieval_logs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_app_settings_key', table_name='app_settings')
    op.drop_table('app_settings')

    op.drop_index('ix_retrieval_logs_session_id', table_name='retrieval_logs')
    op.drop_index('ix_retrieval_logs_id', table_name='retrieval_logs')
    op.drop_table('retrieval_logs')

    op.drop_index('ix_feedback_message_id', table_name='feedback')
    op.drop_index('ix_feedback_id', table_name='feedback')
    op.drop_table('feedback')

    op.drop_index('ix_chat_messages_session_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_id', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_id', table_name='chat_sessions')
    op.drop_table('chat_sessions')

    op.execute('DROP INDEX IF EXISTS ix_chunks_embedding_ivfflat')
    op.drop_index('ix_chunks_document_id', table_name='chunks')
    op.drop_index('ix_chunks_id', table_name='chunks')
    op.drop_table('chunks')

    op.drop_index('ix_document_tags_tag_id', table_name='document_tags')
    op.drop_table('document_tags')

    op.drop_index('ix_documents_original_name', table_name='documents')
    op.drop_index('ix_documents_owner_id', table_name='documents')
    op.drop_index('ix_documents_id', table_name='documents')
    op.drop_table('documents')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')

    op.drop_index('ix_tags_name', table_name='tags')
    op.drop_index('ix_tags_id', table_name='tags')
    op.drop_table('tags')

    op.drop_index('ix_departments_name', table_name='departments')
    op.drop_index('ix_departments_id', table_name='departments')
    op.drop_table('departments')

    sa.Enum(name='feedback_rating_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='chat_role_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='document_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='document_visibility_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='role_enum').drop(op.get_bind(), checkfirst=True)
