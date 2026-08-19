"""Схемы для ручных рассылок из админки (admin_mailings)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionLevelFilter(BaseModel):
    """Условие фильтрации по уровню подписки."""

    gte: int = Field(
        ..., description="Минимальный уровень подписки (включительно)"
    )


class AudienceFilter(BaseModel):
    """Фильтр аудитории рассылки."""

    subscription_level: SubscriptionLevelFilter | None = Field(
        default=None, description="Без фильтра. Все активные пользователи"
    )


class AdminMailing(BaseModel):
    """Уведомления из админки."""

    admin_mailing_id: UUID
    template_id: UUID
    audience_filter: dict[str, Any]
    payload: dict[str, Any]
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    created_by: UUID

    model_config = {"from_attributes": True}


class AdminMailingCreate(BaseModel):
    """Запрос на создание рассылки."""

    template_id: UUID = Field(..., description="Шаблон для рендера")
    audience_filter: AudienceFilter = Field(default_factory=AudienceFilter)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description=("Данные для подстановки в шаблон"),
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Когда отправить. Если не указывать, то отправить сразу",
    )
    created_by: UUID = Field(
        ..., description="Администратор, создающий рассылку"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "template_id": "daee7e9a-d79e-4a1e-9802-0ce1f666f990",
                    "audience_filter": {"subscription_level": {"gte": 1}},
                    "payload": {},
                    "scheduled_at": None,
                    "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                }
            ]
        }
    }
