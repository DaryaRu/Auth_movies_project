"""API version 1."""

from src.api.v1.bookmarks import router as bookmarks_router
from src.api.v1.likes import router as likes_router
from src.api.v1.review_likes import router as review_likes_router
from src.api.v1.reviews import router as reviews_router

__all__ = ["bookmarks_router", "likes_router", "review_likes_router", "reviews_router"]
