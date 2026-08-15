"""Репозиторий для настроек уведомлений пользователя."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class UserNotificationSettingsRepository:
    """Репозиторий для user_notification_settings."""

    async def get_by_user_id(self, user_id: UUID) -> dict[str, Any] | None:
        """Получить настройки пользователя для уведомлений.
        Все каналы default true, кроме sms."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_notification_settings WHERE user_id = $1",
                user_id,
            )
        return dict(row) if row else None
