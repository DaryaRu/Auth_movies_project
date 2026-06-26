"""seed_free_subscription

Revision ID: b3e1f2a4c8d0
Revises: 942d946b7ded
Create Date: 2026-06-26 15:57:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e1f2a4c8d0"
down_revision: Union[str, Sequence[str], None] = "942d946b7ded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить дефолтную подписку free."""
    op.execute(
        sa.text(
            """
            INSERT INTO subscriptions (id, code, description, level, is_active, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                'free',
                'Общедоступный контент',
                0,
                true,
                now(),
                now()
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    """Удалить дефолтную подписку free."""
    op.execute(sa.text("DELETE FROM subscriptions WHERE code = 'free'"))
