"""API endpoints для лайков рецензий."""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.v1.dependencies import CurrentUserDep
from src.core.config import settings
from src.repositories.review_likes import ReviewLikeRepository
from src.schemas.review_likes import (
    ReviewLikeCreate,
    ReviewLikeResponse,
    ReviewLikesListResponse,
    ReviewLikeStatsResponse,
)
from src.services.review_likes import ReviewLikeService

router = APIRouter(prefix="/user-actions/review-likes", tags=["review-likes"])
limiter = Limiter(key_func=get_remote_address)


def get_review_like_service() -> ReviewLikeService:
    """Получить сервис лайков рецензий."""
    repository = ReviewLikeRepository()
    return ReviewLikeService(repository)


ReviewLikeServiceDep = Depends(get_review_like_service)


@router.post(
    "/",
    response_model=ReviewLikeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Поставить лайк или дизлайк рецензии",
    description="Поставить лайк (is_like=true) или дизлайк (is_like=false) рецензии. При повторном запросе обновляется.",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def create_or_update_review_like(
    request: Request,
    like_data: ReviewLikeCreate,
    user_id: CurrentUserDep,
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> ReviewLikeResponse:
    """Создать или обновить лайк рецензии."""
    try:
        result = await review_like_service.create_or_update_review_like(
            user_id, like_data.review_id, like_data.is_like
        )
        return ReviewLikeResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/review/{review_id}",
    response_model=ReviewLikesListResponse,
    summary="Лайки рецензии",
    description="Получить список лайков для конкретной рецензии",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def get_review_likes(
    request: Request,
    review_id: UUID = Path(..., description="UUID рецензии"),
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> ReviewLikesListResponse:
    """Получить лайки рецензии."""
    items = await review_like_service.get_review_likes(review_id)
    return ReviewLikesListResponse(items=items, total=len(items))


@router.get(
    "/review/{review_id}/stats",
    response_model=ReviewLikeStatsResponse,
    summary="Статистика лайков рецензии",
    description="Получить статистику лайков для рецензии: количество лайков, дизлайков и общий счёт",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def get_review_stats(
    request: Request,
    review_id: UUID = Path(..., description="UUID рецензии"),
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> ReviewLikeStatsResponse:
    """Получить статистику лайков рецензии."""
    stats = await review_like_service.get_review_stats(review_id)
    return ReviewLikeStatsResponse(**stats)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить лайк рецензии",
    description="Удалить лайк для рецензии",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def delete_review_like(
    request: Request,
    user_id: CurrentUserDep,
    review_id: UUID = Path(..., description="UUID рецензии"),
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> None:
    """Удалить лайк рецензии."""
    deleted = await review_like_service.delete_review_like(user_id, review_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Review like not found",
        )
