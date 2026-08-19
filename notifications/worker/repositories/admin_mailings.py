"""Репозиторий рассылок (admin_mailings) для воркера."""

from uuid import UUID

from db.postgres import PostgreSQL


class AdminMailingsRepository:
    """Репозиторий для работы с admin_mailings."""

    async def mark_mailing_sent(self, admin_mailing_id: UUID) -> None:
        """Отметить рассылку как полностью обработанную."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE admin_mailings
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                WHERE admin_mailing_id = $1
                """,
                admin_mailing_id,
            )

    async def mark_mailing_failed(self, admin_mailing_id: UUID) -> None:
        """Отметить рассылку как не обработанную целиком (если сбой до начала прохода по получателям)."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                "UPDATE admin_mailings SET status = 'failed' WHERE admin_mailing_id = $1",
                admin_mailing_id,
            )
