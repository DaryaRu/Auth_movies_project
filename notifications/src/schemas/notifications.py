"""Схемы для персональных уведомлений."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    """Запрос на персональное уведомление (user_id известен вызывающему сервису."""

    user_id: UUID = Field(..., description="Получатель")
    template_id: UUID = Field(..., description="Шаблон сообщения")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Данные для подстановки в шаблон (должны совпадать с allowed_variables шаблона)",
    )
