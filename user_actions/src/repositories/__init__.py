"""Репозитории для работы с данными."""

from src.repositories.bookmarks import BookmarkRepository
from src.repositories.likes import LikeRepository
from src.repositories.reviews import ReviewRepository

__all__ = ["BookmarkRepository", "LikeRepository", "ReviewRepository"]