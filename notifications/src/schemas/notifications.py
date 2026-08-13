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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "template_id": "daee7e9a-d79e-4a1e-9802-0ce1f666f990",
                    "payload": {
                        "liker_name": "Василий",
                        "movie_title": "Алиса в стране чудес",
                    },
                }
            ]
        }
    }
