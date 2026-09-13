"""add nickname to users

Revision ID: d4e9f2a8c167
Revises: e6d377e2c5d3
Create Date: 2026-12-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e9f2a8c167"
down_revision: Union[str, Sequence[str], None] = "e6d377e2c5d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле nickname в таблицу users.

    nickname — публичный никнейм пользователя, задаётся в профиле.
    Используется как один из вариантов отображения автора рецензии
    (author_visibility='nickname').
    """
    op.add_column(
        "users",
        sa.Column("nickname", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Удалить поле nickname из таблицы users."""
    op.drop_column("users", "nickname")
