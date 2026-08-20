"""Репозиторий рассылок (admin_mailings) для шедулера."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class AdminMailingsRepository:
    """Репозиторий для чтения отложенных рассылок, время которых наступило."""

    async def get_due_scheduled_mailings(self) -> list[dict[str, Any]]:
        """Рассылки со status=scheduled, у которых наступило scheduled_at."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM admin_mailings
                WHERE status = 'scheduled' AND scheduled_at <= CURRENT_TIMESTAMP
                """
            )
        return [dict(row) for row in rows]

    async def mark_mailing_sending(self, admin_mailing_id: UUID) -> None:
        """Отметить рассылку как переданную в обработку."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            await conn.execute(
                "UPDATE admin_mailings SET status = 'sending' WHERE admin_mailing_id = $1",
                admin_mailing_id,
            )
