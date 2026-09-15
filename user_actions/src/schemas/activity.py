"""Схема ответа для активности пользователя в профиле пользователя."""

from pydantic import BaseModel

from src.schemas.bookmarks import BookmarkResponse
from src.schemas.likes import LikeResponse
from src.schemas.reviews import ReviewResponse


class UserActivityResponse(BaseModel):
    """Последние закладки, оценки и рецензии пользователя."""

    bookmarks: list[BookmarkResponse]
    likes: list[LikeResponse]
    reviews: list[ReviewResponse]
