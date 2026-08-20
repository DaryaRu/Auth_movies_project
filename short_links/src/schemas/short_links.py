"""Схемы для коротких ссылок."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ShortLinkBase(BaseModel):
    """Базовая схема короткой ссылки."""

    short_key: str
    user_id: UUID
    expires_at: datetime
    redirect_url: str
    is_used: bool = False
    created_at: datetime | None = None


class ShortLink(ShortLinkBase):
    """Короткая ссылка."""

    id: UUID

    model_config = {"from_attributes": True}


class ShortLinkCreate(BaseModel):
    """Запрос на создание короткой ссылки."""

    user_id: UUID = Field(description="ID пользователя")
    expires_at: datetime = Field(description="Срок действия ссылки")
    redirect_url: str = Field(description="URL для редиректа после подтверждения")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "expires_at": "2026-08-18T10:00:00Z",
                    "redirect_url": "http://localhost/",
                }
            ]
        }
    }


class ShortLinkResponse(BaseModel):
    """Ответ с созданной короткой ссылкой."""

    short_key: str = Field(description="Короткий ключ ссылки")
    short_link: str = Field(description="Полная короткая ссылка")
    expires_at: datetime = Field(description="Срок действия ссылки")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "short_key": "aB3dE5",
                    "short_link": "http://localhost/c/aB3dE5",
                    "expires_at": "2026-08-18T10:00:00Z",
                }
            ]
        }
    }