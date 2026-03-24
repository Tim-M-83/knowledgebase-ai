"""add chat session type and email helper flag

Revision ID: 20260319_0004
Revises: 20260319_0003
Create Date: 2026-03-19 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '20260319_0004'
down_revision: Union[str, Sequence[str], None] = '20260319_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    session_type_enum = postgresql.ENUM('chat', 'email_helper', name='chat_session_type_enum', create_type=False)
    session_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'chat_sessions',
        sa.Column(
            'session_type',
            session_type_enum,
            nullable=True,
            server_default=sa.text("'chat'"),
        ),
    )
    op.execute("UPDATE chat_sessions SET session_type = 'chat' WHERE session_type IS NULL")
    op.alter_column('chat_sessions', 'session_type', server_default=None, nullable=False)
    op.create_index('ix_chat_sessions_session_type', 'chat_sessions', ['session_type'], unique=False)

    op.execute(
        """
        INSERT INTO app_settings (key, value)
        SELECT 'email_helper_enabled', 'true'
        WHERE NOT EXISTS (
            SELECT 1 FROM app_settings WHERE key = 'email_helper_enabled'
        )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM app_settings WHERE key = 'email_helper_enabled'")

    op.drop_index('ix_chat_sessions_session_type', table_name='chat_sessions')
    op.drop_column('chat_sessions', 'session_type')

    session_type_enum = postgresql.ENUM('chat', 'email_helper', name='chat_session_type_enum', create_type=False)
    session_type_enum.drop(op.get_bind(), checkfirst=True)
