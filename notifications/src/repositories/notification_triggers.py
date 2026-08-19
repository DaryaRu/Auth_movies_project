"""Репозиторий для триггеров уведомлений (notification_triggers)."""

from typing import Any
from uuid import UUID

from asyncpg import Record

from src.db.postgres import PostgreSQL
from src.schemas.triggers import NotificationTrigger


def _row_to_trigger(row: Record) -> NotificationTrigger:
    return NotificationTrigger.model_validate(dict(row))


class NotificationTriggerRepository:
    """Репозиторий для работы с notification_triggers."""

    async def upsert(
        self,
        content_id: UUID,
        notification_type: str,
        template_id: UUID,
        payload: dict[str, Any],
    ) -> NotificationTrigger:
        """Upsert по (content_id, notification_type).

        Если записи с (content_id, notification_type) не было - создается,
        если была — обновляются template_id/payload/last_update.
        """
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notification_triggers
                    (content_id, notification_type, template_id, payload, last_update)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (content_id, notification_type) DO UPDATE SET
                    template_id = EXCLUDED.template_id,
                    payload = EXCLUDED.payload,
                    last_update = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                content_id,
                notification_type,
                template_id,
                payload,
            )
        assert row is not None
        return _row_to_trigger(row)
