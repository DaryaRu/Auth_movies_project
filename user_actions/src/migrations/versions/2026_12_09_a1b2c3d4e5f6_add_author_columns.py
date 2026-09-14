"""add author_visibility and author_name columns to reviews

Revision ID: a1b2c3d4e5f6
Revises: eb707e76b7fd
Create Date: 2026-12-09

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'eb707e76b7fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить колонки author_visibility и author_name в таблицу reviews.
    
    author_visibility: 'real_name' или 'anonymous' — выбор пользователя,
        показывать имя автора рецензии или нет.
    
    author_name: snapshot full_name из auth-сервиса (сохраняется при создании
        рецензии, не обновляется).
    """
    op.execute(
        "ALTER TABLE reviews "
        "ADD COLUMN IF NOT EXISTS author_visibility TEXT NOT NULL DEFAULT 'real_name'"
    )
    op.execute(
        "ALTER TABLE reviews "
        "ADD COLUMN IF NOT EXISTS author_name TEXT NOT NULL DEFAULT 'Аноним'"
    )
    op.execute(
        "ALTER TABLE reviews "
        "ADD CONSTRAINT reviews_author_visibility_check "
        "CHECK (author_visibility IN ('real_name', 'anonymous'))"
    )


def downgrade() -> None:
    """Удалить колонки author_visibility и author_name."""
    op.execute(
        "ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_author_visibility_check"
    )
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS author_visibility")
    op.execute("ALTER TABLE reviews DROP COLUMN IF EXISTS author_name")