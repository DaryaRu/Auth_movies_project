"""add email_verified to users

Revision ID: a1b2c3d4e5f6
Revises: b3e1f2a4c8d0
Create Date: 2026-08-17 22:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b3e1f2a4c8d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить поле email_verified в таблицу users."""
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Удалить поле email_verified из таблицы users."""
    op.drop_column("users", "email_verified")