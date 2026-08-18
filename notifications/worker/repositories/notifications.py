"""Репозиторий уведомлений (notifications)."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class NotificationsRepository:
    """Репозиторий для notifications."""

    async def get_or_create(
        self,
        deduplication_key: str,
        user_id: UUID,
        notification_type: str | None,
        template_id: UUID | None,
        channel: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        """Идемпотентно создает запись по deduplication_key (если такая уже есть, то возвращает существующую) -
        защищает от повторной обработки одного и того же Kafka-сообщения.

        Возвращает (notification, created). Флаг created=True означает, что сообщение обрабатывается впервые.
        Флаг created=False - уже существовало.
        """
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notifications
                    (user_id, notification_type, template_id, channel, payload, deduplication_key, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                ON CONFLICT (deduplication_key) DO NOTHING
                RETURNING *
                """,
                user_id,
                notification_type,
                template_id,
                channel,
                payload,
                deduplication_key,
            )
            if row is not None:
                return dict(row), True

            existing = await conn.fetchrow(
                "SELECT * FROM notifications WHERE deduplication_key = $1",
                deduplication_key,
            )
            assert existing is not None
            return dict(existing), False

    async def mark_notification_sent(
        self, notification_id: UUID, delivery_address: str
    ) -> None:
        """Отметить уведомление как отправленное."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notifications
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP,
                    delivery_address = $2, error_message = NULL
                WHERE notification_id = $1
                """,
                notification_id,
                delivery_address,
            )

    async def mark_notification_failed(
        self, notification_id: UUID, error_message: str
    ) -> None:
        """Отметить уведомление как неудавшееся."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE notifications
                SET status = 'failed', error_message = $2
                WHERE notification_id = $1
                """,
                notification_id,
                error_message,
            )

    async def mark_notification_skipped(self, notification_id: UUID) -> None:
        """Отметить уведомление как пропущенное (пользователь отключил уведомления)."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                "UPDATE notifications SET status = 'skipped' WHERE notification_id = $1",
                notification_id,
            )
