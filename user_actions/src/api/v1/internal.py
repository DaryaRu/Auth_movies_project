"""Внутренние эндпоинты"""

from uuid import UUID

from fastapi import APIRouter

from src.api.v1.dependencies import InternalServiceDep
from src.repositories.bookmarks import BookmarkRepository

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get(
    "/bookmarks/{content_id}/users/",
    summary="Пользователи, добавившие content_id в закладки",
)
async def get_bookmark_user_ids(
    content_id: UUID, _: InternalServiceDep
) -> list[UUID]:
    """Получить пользователей, добавивших content_id в закладки."""
    repository = BookmarkRepository()
    return await repository.get_movie_bookmark_user_ids(content_id)
