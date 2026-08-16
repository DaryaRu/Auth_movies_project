"""Репозиторий для шаблонов сообщений."""

from typing import Any
from uuid import UUID

from asyncpg import Record

from src.db.postgres import PostgreSQL
from src.schemas.templates import Template


def _row_to_template(row: Record) -> Template:
    return Template.model_validate(dict(row))


class TemplateRepository:
    """Репозиторий для работы с шаблонами."""

    async def get_by_id(self, template_id: UUID) -> Template | None:
        """Получить шаблон по ID."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM templates WHERE template_id = $1", template_id
            )
        return _row_to_template(row) if row else None

    async def get_by_code(self, code: str) -> Template | None:
        """Получить шаблон по code."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM templates WHERE code = $1", code
            )
        return _row_to_template(row) if row else None

    async def list_all(self) -> list[Template]:
        """Получить все шаблоны."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM templates ORDER BY created_at DESC"
            )
        return [_row_to_template(row) for row in rows]

    async def create(self, data: dict[str, Any]) -> Template:
        """Создать шаблон."""
        columns = list(data.keys())
        placeholders = [f"${i + 1}" for i in range(len(columns))]
        query = (
            f"INSERT INTO templates ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, *data.values())
        assert row is not None
        return _row_to_template(row)

    async def update(
        self, template_id: UUID, data: dict[str, Any]
    ) -> Template | None:
        """Частично обновить шаблон."""
        columns = list(data.keys())
        set_parts = [
            f"{column} = ${i + 1}" for i, column in enumerate(columns)
        ]
        values = list(data.values()) + [template_id]
        query = (
            f"UPDATE templates SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP "
            f"WHERE template_id = ${len(values)} RETURNING *"
        )
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
        return _row_to_template(row) if row else None
