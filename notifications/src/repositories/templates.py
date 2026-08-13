"""Репозиторий для шаблонов сообщений."""

import json
from uuid import UUID

from src.db.postgres import PostgreSQL
from src.schemas.templates import Template


class TemplateRepository:
    """Репозиторий для работы с шаблонами."""

    async def get_by_id(self, template_id: UUID) -> Template | None:
        """Получить шаблон по ID."""
        assert PostgreSQL.pool is not None
        async with PostgreSQL.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM templates WHERE template_id = $1", template_id
            )
        if row is None:
            return None
        data = dict(row)

        if isinstance(data["allowed_variables"], str):
            data["allowed_variables"] = json.loads(data["allowed_variables"])
        return Template.model_validate(data)
