"""add full_name to users

Revision ID: 8105788f98b7
Revises: b563de01be48
Create Date: 2026-09-01 14:23:57.481932

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8105788f98b7"
down_revision: Union[str, Sequence[str], None] = "b563de01be48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле full_name в таблицу users."""
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Удалить поле full_name из таблицы users."""
    op.drop_column("users", "full_name")
