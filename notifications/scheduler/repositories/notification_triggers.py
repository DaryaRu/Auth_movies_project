"""Репозиторий триггеров уведомлений (notification_triggers) для шедулера."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class NotificationTriggersRepository:
    """Репозиторий для чтения триггеров, которые пора проверять."""

    async def get_triggers_to_check(self) -> list[dict[str, Any]]:
        """Активные триггеры, для которых наступило время проверки."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM notification_triggers
                WHERE is_active = true
                  AND (last_checked_at IS NULL OR CURRENT_TIMESTAMP >= last_checked_at + check_interval)
                """
            )
        return [dict(row) for row in rows]

    async def mark_trigger_checked(self, trigger_id: UUID) -> None:
        """Обновить last_checked_at для проверенных триггеров."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                "UPDATE notification_triggers SET last_checked_at = CURRENT_TIMESTAMP WHERE trigger_id = $1",
                trigger_id,
            )
