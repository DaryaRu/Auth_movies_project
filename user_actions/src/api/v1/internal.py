"""Внутренние эндпоинты"""

from uuid import UUID

from fastapi import APIRouter, status

from src.api.v1.dependencies import InternalServiceDep
from src.core.config import settings
from src.repositories.bookmarks import BookmarkRepository
from src.repositories.likes import LikeRepository
from src.repositories.review_likes import ReviewLikeRepository
from src.repositories.reviews import ReviewRepository
from src.schemas.activity import UserActivityResponse
from src.services.bookmarks import BookmarkService
from src.services.likes import LikeService
from src.services.review_likes import ReviewLikeService
from src.services.reviews import ReviewService

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


@router.get(
    "/users/{user_id}/activity/",
    response_model=UserActivityResponse,
    summary="Закладки, оценки и рецензии пользователя",
)
async def get_user_activity(
    user_id: UUID, _: InternalServiceDep
) -> UserActivityResponse:
    """Отдает последнюю страницу (PAGINATION_DEFAULT_PAGE_SIZE)
    каждого типа активности, без пагинации."""
    limit = settings.PAGINATION_DEFAULT_PAGE_SIZE

    bookmarks, _bookmarks_total = await BookmarkService(
        BookmarkRepository()
    ).get_user_bookmarks(user_id, page=1, page_size=limit)
    likes, _likes_total = await LikeService(LikeRepository()).get_user_likes(
        user_id, page=1, page_size=limit
    )
    review_result = await ReviewService(ReviewRepository()).get_user_reviews(
        user_id, page=1, page_size=limit
    )
    review_items = review_result["items"]
    review_ids = [item["id"] for item in review_items]
    likes_stats = await ReviewLikeService(
        ReviewLikeRepository()
    ).get_reviews_stats(review_ids)
    reviews = []
    for item in review_items:
        stats = likes_stats.get(
            item["id"], {"likes": 0, "dislikes": 0, "total": 0, "score": 0}
        )
        reviews.append(
            {
                **item,
                "likes_count": stats["likes"],
                "dislikes_count": stats["dislikes"],
                "score": stats["score"],
            }
        )

    return UserActivityResponse(
        bookmarks=bookmarks, likes=likes, reviews=reviews
    )
