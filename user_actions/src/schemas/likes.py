"""Схемы для лайков."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LikeBase(BaseModel):
    """Базовая схема лайка."""

    movie_id: UUID = Field(..., description="UUID фильма")
    rating: int = Field(..., ge=0, le=10, description="Оценка от 0 до 10 (0 - дизлайк, 10 - лайк)")


class LikeCreate(LikeBase):
    """Схема для создания лайка."""

    pass


class LikeResponse(LikeBase):
    """Схема ответа лайка."""

    id: UUID = Field(..., description="ID лайка")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    model_config = {"from_attributes": True}


class LikesListResponse(BaseModel):
    """Схема ответа списка лайков."""

    items: list[LikeResponse]
    total: int


class LikeStatsResponse(BaseModel):
    """Схема ответа статистики лайков."""

    likes: int = Field(..., description="Количество лайков (оценка 10)")
    dislikes: int = Field(..., description="Количество дизлайков (оценка 0)")
    total: int = Field(..., description="Общее количество оценок")
    average_rating: float = Field(..., description="Средняя пользовательская оценка")
