"""Репозиторий для ручных рассылок из админки (admin_mailings)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from asyncpg import Record

from src.db.postgres import PostgreSQL
from src.schemas.admin_mailings import AdminMailing


def _row_to_mailing(row: Record) -> AdminMailing:
    return AdminMailing.model_validate(dict(row))


class AdminMailingRepository:
    """Репозиторий для работы с admin_mailings."""

    async def create(
        self,
        template_id: UUID,
        audience_filter: dict[str, Any],
        payload: dict[str, Any],
        status: str,
        scheduled_at: datetime | None,
        created_by: UUID,
    ) -> AdminMailing:
        """Создать рассылку."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO admin_mailings
                    (template_id, audience_filter, payload, status, scheduled_at, created_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                template_id,
                audience_filter,
                payload,
                status,
                scheduled_at,
                created_by,
            )
        assert row is not None
        return _row_to_mailing(row)

    async def get_by_id(self, admin_mailing_id: UUID) -> AdminMailing | None:
        """Получить рассылку по ID."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM admin_mailings WHERE admin_mailing_id = $1",
                admin_mailing_id,
            )
        return _row_to_mailing(row) if row else None

    async def list_all(self) -> list[AdminMailing]:
        """Получить все рассылки."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM admin_mailings ORDER BY created_at DESC"
            )
        return [_row_to_mailing(row) for row in rows]
