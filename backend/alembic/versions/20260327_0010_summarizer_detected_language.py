"""add detected language to summarizer documents

Revision ID: 20260327_0010
Revises: 20260323_0009
Create Date: 2026-03-27 09:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260327_0010'
down_revision: Union[str, Sequence[str], None] = '20260323_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('summarizer_documents', sa.Column('detected_language_code', sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column('summarizer_documents', 'detected_language_code')
