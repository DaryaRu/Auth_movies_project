"""Схемы для ручных рассылок из админки (admin_mailings)."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator

LOCAL_TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


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
    timezone: str | None = Field(
        default=None,
        description=("Заполняется автоматически при scheduled_local_time."),
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
    scheduled_at: AwareDatetime | None = Field(
        default=None,
        description=(
            "Когда отправить (с таймзоной, например "
            "2057-07-27T10:00:00+00:00). Если не указывать, то отправить сразу"
        ),
    )
    scheduled_local_time: str | None = Field(
        default=None,
        description=(
            "Локальное время получателя вида HH:MM (например 10:00). "
            "Рассылка будет разбита по таймзонам аудитории. "
            "Для каждой отдельная рассылка на ближайшее наступление этого "
            "времени в соответствующей таймзоне."
        ),
    )
    created_by: UUID = Field(
        ..., description="Администратор, создающий рассылку"
    )

    @model_validator(mode="after")
    def validate_scheduling(self):
        if (
            self.scheduled_at is not None
            and self.scheduled_local_time is not None
        ):
            raise ValueError(
                "Нельзя одновременно указывать scheduled_at и scheduled_local_time"
            )
        if (
            self.scheduled_local_time is not None
            and not LOCAL_TIME_REGEX.match(self.scheduled_local_time)
        ):
            raise ValueError(
                f"Некорректный формат scheduled_local_time (ожидается HH:MM): {self.scheduled_local_time}"
            )
        return self

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
