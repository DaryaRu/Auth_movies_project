"""add nickname option to reviews author_visibility

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-12-09

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Расширить author_visibility: добавить вариант 'nickname'.

    Теперь автор рецензии может выбрать, как отображать себя:
    'real_name' (ФИО), 'nickname' (никнейм из auth) или 'anonymous' (Аноним).
    """
    op.execute(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_author_visibility_check"
    )
    op.execute(
        "ALTER TABLE reviews "
        "ADD CONSTRAINT reviews_author_visibility_check "
        "CHECK (author_visibility IN ('real_name', 'nickname', 'anonymous'))"
    )


def downgrade() -> None:
    """Вернуть author_visibility к вариантам 'real_name' и 'anonymous'."""
    op.execute(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_author_visibility_check"
    )
    op.execute(
        "ALTER TABLE reviews "
        "ADD CONSTRAINT reviews_author_visibility_check "
        "CHECK (author_visibility IN ('real_name', 'anonymous'))"
    )
