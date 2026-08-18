"""Схемы для триггеров уведомлений (Scheduled group)."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationTrigger(BaseModel):
    """Триггер уведомления."""

    trigger_id: UUID
    notification_type: str
    content_id: UUID
    template_id: UUID
    payload: dict[str, Any]
    last_update: datetime
    last_notification_sent: datetime | None
    check_interval: timedelta
    last_checked_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class NotificationTriggerUpsert(BaseModel):
    """Upsert триггера уведомления по (content_id, notification_type)."""

    content_id: UUID = Field(
        ..., description="Сущность, на изменение которой реагирует уведомление"
    )
    notification_type: str = Field(
        ...,
        description="Определяет логику подбора аудитории, например new_episode",
    )
    template_id: UUID = Field(..., description="Шаблон для рендера")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Данные для рендера на момент последнего изменения",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "notification_type": "new_episode",
                    "template_id": "daee7e9a-d79e-4a1e-9802-0ce1f666f990",
                    "payload": {},
                }
            ]
        }
    }
