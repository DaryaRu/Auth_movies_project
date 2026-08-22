"""add timezone to users

Revision ID: b563de01be48
Revises: a1b2c3d4e5f6
Create Date: 2026-08-22 16:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b563de01be48"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле timezone (IANA-имя, например Europe/Moscow) в таблицу users."""
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    """Удалить поле timezone из таблицы users."""
    op.drop_column("users", "timezone")
