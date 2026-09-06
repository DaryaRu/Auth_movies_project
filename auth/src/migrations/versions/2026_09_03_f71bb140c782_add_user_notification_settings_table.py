"""add user notification settings table

Revision ID: f71bb140c782
Revises: b563de01be48
Create Date: 2026-09-03 10:14:12.830870

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f71bb140c782'
down_revision: Union[str, Sequence[str], None] = 'b563de01be48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_notification_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            notifications_enabled BOOLEAN NOT NULL DEFAULT true,
            email_enabled BOOLEAN NOT NULL DEFAULT true,
            sms_enabled BOOLEAN NOT NULL DEFAULT false,
            push_enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_notification_settings_user_id "
        "ON user_notification_settings(user_id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS user_notification_settings")
