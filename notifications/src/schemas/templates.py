"""Схемы для шаблонов сообщений."""

from uuid import UUID

from pydantic import BaseModel


class Template(BaseModel):
    """Шаблоны сообщений."""

    template_id: UUID
    code: str
    name: str
    channel: str
    subject: str | None
    body: str
    allowed_variables: list[str]
    is_active: bool

    model_config = {"from_attributes": True}
