"""Схемы для шаблонов сообщений."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

Channel = Literal["email", "sms", "push"]


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


class TemplateCreate(BaseModel):
    """Создание шаблона."""

    code: str
    name: str
    channel: Channel
    subject: str | None = None
    body: str
    allowed_variables: list[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "comment_liked",
                    "name": "Лайк на комментарий (email)",
                    "channel": "email",
                    "subject": "Ваш комментарий оценили",
                    "body": "Пользователь поставил лайк на ваш комментарий.",
                    "allowed_variables": [],
                    "is_active": True,
                }
            ]
        }
    }


class TemplateUpdate(BaseModel):
    """Редактирование шаблона."""

    name: str | None = None
    channel: Channel | None = None
    subject: str | None = None
    body: str | None = None
    allowed_variables: list[str] | None = None
    is_active: bool | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "body": "Пользователь поставил лайк на ваш комментарий.",
                    "is_active": True,
                }
            ]
        }
    }


class TemplatePreviewRequest(BaseModel):
    """Тестовый payload для превью рендера шаблона."""

    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"payload": {}},
            ]
        }
    }


class TemplatePreviewResponse(BaseModel):
    """Результат рендера."""

    subject: str | None
    body: str
