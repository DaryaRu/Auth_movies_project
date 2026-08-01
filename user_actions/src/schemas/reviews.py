"""Схемы для рецензий."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewBase(BaseModel):
    """Базовая схема рецензии.
    
    Рецензия состоит из трёх составляющих:
    1. Текст рецензии — пользовательское мнение о фильме
    2. Дополнительные данные — дата публикации, автор (user_id)
    3. Данные из смежных таблиц — лайки/дизлайки рецензии, оценка фильма
    """

    movie_id: UUID = Field(..., description="UUID фильма")
    text: str = Field(..., min_length=10, max_length=5000, description="Текст рецензии")
    rating: int = Field(
        ...,
        ge=1,
        le=10,
        description="Оценка фильма пользователем (привязана к рецензии). Шкала от 1 (худший фильм) до 10 (лучший фильм)"
    )


class ReviewCreate(ReviewBase):
    """Схема для создания рецензии."""

    pass


class ReviewUpdate(BaseModel):
    """Схема для обновления рецензии."""
    text: str | None = Field(default=None, min_length=10, max_length=5000, description="Текст рецензии")
    rating: int | None = Field(default=None, ge=1, le=10, description="Оценка от 1 до 10")


class ReviewResponse(ReviewBase):
    """Схема ответа рецензии."""

    id: UUID = Field(..., description="ID рецензии")
    user_id: UUID = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    likes_count: int = Field(default=0, description="Количество лайков рецензии")
    dislikes_count: int = Field(default=0, description="Количество дизлайков рецензии")
    score: int = Field(default=0, description="Разница между лайками и дизлайками")

    model_config = {"from_attributes": True}


class ReviewsListResponse(BaseModel):
    """Схема ответа списка рецензий."""

    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int
