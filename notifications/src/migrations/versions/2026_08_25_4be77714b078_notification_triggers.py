"""notification_triggers

Revision ID: 4be77714b078
Revises: d9332a2ecf59
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4be77714b078'
down_revision: Union[str, Sequence[str], None] = 'd9332a2ecf59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Триггеры уведомлений для периодических групповых уведомлений (Scheduled group)."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_triggers (
            trigger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            -- Тип уведомления определяет логику подбора аудитории воркером.
            notification_type VARCHAR(255) NOT NULL,
            -- Сущность, на изменение которой реагирует уведомление (например, ID сериала).
            content_id UUID NOT NULL,
            template_id UUID NOT NULL REFERENCES templates(template_id),
            -- Данные для рендера на момент последнего изменения контента.
            payload JSONB NOT NULL DEFAULT '{}',
            -- Когда контент реально изменился.
            last_update TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            -- Когда последний раз реально отправляли уведомление. Обновляется воркером.
            last_notification_sent TIMESTAMP WITH TIME ZONE,
            -- Как часто шедулер должен проверять этот триггер.
            check_interval INTERVAL NOT NULL DEFAULT '1 hour',
            -- Когда шедулер последний раз проверял триггер.
            last_checked_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (content_id, notification_type)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_triggers_content_id "
        "ON notification_triggers(content_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_triggers_is_active "
        "ON notification_triggers(is_active)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS notification_triggers")
