"""Схемы для лайков рецензий."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewLikeBase(BaseModel):
    """Базовая схема лайка рецензии."""

    review_id: UUID = Field(..., description="UUID рецензии")
    is_like: bool = Field(..., description="true - лайк, false - дизлайк")


class ReviewLikeCreate(ReviewLikeBase):
    """Схема для создания лайка рецензии."""

    pass


class ReviewLikeResponse(ReviewLikeBase):
    """Схема ответа лайка рецензии."""

    id: UUID = Field(..., description="ID лайка рецензии")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")

    model_config = {"from_attributes": True}


class ReviewLikesListResponse(BaseModel):
    """Схема ответа списка лайков рецензии."""

    items: list[ReviewLikeResponse]
    total: int


class ReviewLikeStatsResponse(BaseModel):
    """Схема ответа статистики лайков рецензии."""

    likes: int = Field(..., description="Количество лайков")
    dislikes: int = Field(..., description="Количество дизлайков")
    total: int = Field(..., description="Общее количество голосов")
    score: int = Field(..., description="Разница между лайками и дизлайками (likes - dislikes)")
