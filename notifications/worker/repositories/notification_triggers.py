"""Репозиторий триггеров уведомлений (notification_triggers) для воркера."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class NotificationTriggersRepository:
    """Репозиторий для чтения/обновления notification_triggers."""

    async def get_by_content_and_type(
        self, content_id: UUID, notification_type: str
    ) -> dict[str, Any] | None:
        """Получить notification_trigger по (content_id, notification_type)."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM notification_triggers
                WHERE content_id = $1 AND notification_type = $2
                """,
                content_id,
                notification_type,
            )
        return dict(row) if row else None

    async def mark_trigger_sent(self, trigger_id: UUID) -> None:
        """Отметить, что уведомление по этому notification_trigger отправлено."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notification_triggers
                SET last_notification_sent = CURRENT_TIMESTAMP
                WHERE trigger_id = $1
                """,
                trigger_id,
            )
