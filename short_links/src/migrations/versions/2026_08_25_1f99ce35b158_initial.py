"""initial

Revision ID: 1f99ce35b158
Revises:
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1f99ce35b158'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Таблица коротких ссылок.

    Каждая команда — отдельный op.execute(): asyncpg через SQLAlchemy
    использует extended query protocol и не может выполнить несколько
    команд в одном execute() (в отличие от простого asyncpg.execute()).
    """
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS short_links (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            short_key     VARCHAR(20) NOT NULL UNIQUE,
            user_id       UUID NOT NULL,
            expires_at    TIMESTAMPTZ NOT NULL,
            redirect_url  VARCHAR(2048) NOT NULL,
            is_used       BOOLEAN NOT NULL DEFAULT FALSE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # Индекс по short_key для быстрого поиска при переходе
    op.execute("CREATE INDEX IF NOT EXISTS idx_short_links_short_key ON short_links(short_key)")
    # Индекс по user_id для поиска ссылок пользователя
    op.execute("CREATE INDEX IF NOT EXISTS idx_short_links_user_id ON short_links(user_id)")
    # Индекс по expires_at для очистки просроченных ссылок
    op.execute("CREATE INDEX IF NOT EXISTS idx_short_links_expires_at ON short_links(expires_at)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS short_links")
