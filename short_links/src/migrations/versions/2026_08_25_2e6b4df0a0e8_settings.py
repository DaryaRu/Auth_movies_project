"""settings

Revision ID: 2e6b4df0a0e8
Revises: 1f99ce35b158
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2e6b4df0a0e8'
down_revision: Union[str, Sequence[str], None] = '1f99ce35b158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Таблица настроек коротких ссылок (redirect_url настраивается из админки)."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key           VARCHAR(100) NOT NULL UNIQUE,
            value         VARCHAR(2048) NOT NULL,
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # Значение по умолчанию: главная страница онлайн-кинотеатра
    op.execute(
        """
        INSERT INTO settings (key, value)
        VALUES ('email_confirmation_redirect_url', 'http://localhost/')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS settings")
