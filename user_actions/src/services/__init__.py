"""Сервисы для работы с данными."""

from src.services.bookmarks import BookmarkService
from src.services.likes import LikeService
from src.services.reviews import ReviewService

__all__ = ["BookmarkService", "LikeService", "ReviewService"]