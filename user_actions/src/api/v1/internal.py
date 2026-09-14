"""Внутренние эндпоинты"""

from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependencies import InternalServiceDep
from src.repositories.bookmarks import BookmarkRepository
from src.repositories.likes import LikeRepository
from src.repositories.review_likes import ReviewLikeRepository
from src.repositories.reviews import ReviewRepository

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


@router.delete(
    "/users/{user_id}/actions/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить все закладки, оценки и рецензии пользователя",
)
async def delete_user_actions(user_id: UUID, _: InternalServiceDep) -> None:
    """Идемпотентно удаляет закладки, оценки фильмов, рецензии и лайки рецензий
    пользователя. Вызывается синхронно auth-service при удалении аккаунта.
    """
    await BookmarkRepository().delete_all_by_user(user_id)
    await LikeRepository().delete_all_by_user(user_id)
    await ReviewLikeRepository().delete_all_by_user(user_id)
    await ReviewRepository().delete_all_by_user(user_id)
