"""seed default departments and set department FK ondelete

Revision ID: 20260319_0003
Revises: 20260303_0002
Create Date: 2026-03-19 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260319_0003'
down_revision: Union[str, Sequence[str], None] = '20260303_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _recreate_department_fk(table_name: str, ondelete: str | None) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    fk_name: str | None = None
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get('referred_table') == 'departments' and fk.get('constrained_columns') == ['department_id']:
            fk_name = fk.get('name')
            break

    if fk_name:
        op.drop_constraint(fk_name, table_name, type_='foreignkey')
    else:
        fk_name = f'{table_name}_department_id_fkey'

    kwargs: dict[str, str] = {}
    if ondelete:
        kwargs['ondelete'] = ondelete

    op.create_foreign_key(fk_name, table_name, 'departments', ['department_id'], ['id'], **kwargs)


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO departments (name)
        SELECT seeded.name
        FROM (VALUES ('HR'), ('Sales'), ('Support')) AS seeded(name)
        WHERE NOT EXISTS (
            SELECT 1
            FROM departments d
            WHERE lower(d.name) = lower(seeded.name)
        )
        """
    )

    _recreate_department_fk('users', ondelete='SET NULL')
    _recreate_department_fk('documents', ondelete='SET NULL')


def downgrade() -> None:
    _recreate_department_fk('users', ondelete=None)
    _recreate_department_fk('documents', ondelete=None)

    op.execute(
        """
        DELETE FROM departments d
        WHERE lower(d.name) IN ('hr', 'sales', 'support')
          AND NOT EXISTS (SELECT 1 FROM users u WHERE u.department_id = d.id)
          AND NOT EXISTS (SELECT 1 FROM documents doc WHERE doc.department_id = d.id)
        """
    )
