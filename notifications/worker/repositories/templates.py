"""Репозиторий для чтения шаблонов."""

from typing import Any
from uuid import UUID

from db.postgres import PostgreSQL


class TemplateRepository:
    """Репозиторий для чтения шаблонов."""

    async def get_by_id(self, template_id: UUID) -> dict[str, Any] | None:
        """Получить шаблон по ID."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM templates WHERE template_id = $1", template_id
            )
        return dict(row) if row else None
