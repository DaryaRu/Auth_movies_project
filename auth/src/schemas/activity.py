"""Схема ответа для активности пользователя в профиле."""

from typing import Any

from pydantic import BaseModel, Field


class UserActivityScheme(BaseModel):
    """Закладки, оценки и рецензии пользователя."""

    bookmarks: list[dict[str, Any]] = Field(default_factory=list)
    likes: list[dict[str, Any]] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
