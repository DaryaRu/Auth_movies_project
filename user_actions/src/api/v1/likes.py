"""API endpoints для лайков."""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.v1.dependencies import CurrentUserDep
from src.core.config import settings
from src.repositories.likes import LikeRepository
from src.schemas.likes import (
    LikeCreate,
    LikeResponse,
    LikesListResponse,
    LikeStatsResponse,
)
from src.services.likes import LikeService

router = APIRouter(prefix="/user-actions/likes", tags=["likes"])
limiter = Limiter(key_func=get_remote_address)


def get_like_service() -> LikeService:
    """Получить сервис лайков."""
    repository = LikeRepository()
    return LikeService(repository)


LikeServiceDep = Depends(get_like_service)


@router.post(
    "/",
    response_model=LikeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Поставить оценку фильму",
    description="Поставить оценку фильму от 0 до 10. При повторном запросе обновляется. 0 - дизлайк, 10 - лайк.",
)
@limiter.limit(settings.LIKES_RATE_LIMIT)
async def create_or_update_like(
    request: Request,
    like_data: LikeCreate,
    user_id: CurrentUserDep,
    like_service: LikeService = LikeServiceDep,
) -> LikeResponse:
    """Создать или обновить оценку."""
    result = await like_service.create_or_update_like(user_id, like_data.movie_id, like_data.rating)
    return LikeResponse(**result)


@router.get(
    "/my",
    response_model=LikesListResponse,
    summary="Мои оценки",
    description="Получить список оценок текущего пользователя",
)
@limiter.limit(settings.LIKES_RATE_LIMIT)
async def get_my_likes(
    request: Request,
    user_id: CurrentUserDep,
    like_service: LikeService = LikeServiceDep,
) -> LikesListResponse:
    """Получить мои оценки."""
    items, total = await like_service.get_user_likes(user_id)
    return LikesListResponse(items=items, total=total)


@router.get(
    "/movie/{movie_id}",
    response_model=list[LikeResponse],
    summary="Оценки фильма",
    description="Получить список оценок для конкретного фильма",
)
@limiter.limit(settings.LIKES_RATE_LIMIT)
async def get_movie_likes(
    request: Request,
    movie_id: UUID = Path(..., description="UUID фильма"),
    like_service: LikeService = LikeServiceDep,
) -> list[LikeResponse]:
    """Получить оценки фильма."""
    likes_list, total = await like_service.get_movie_likes(movie_id)
    return [LikeResponse(**item) for item in likes_list]  # type: ignore[arg-type]


@router.get(
    "/movie/{movie_id}/stats",
    response_model=LikeStatsResponse,
    summary="Статистика оценок фильма",
    description="Получить статистику оценок для фильма: количество лайков, дизлайков, общая оценка и средний рейтинг",
)
@limiter.limit(settings.LIKES_RATE_LIMIT)
async def get_movie_stats(
    request: Request,
    movie_id: UUID = Path(..., description="UUID фильма"),
    like_service: LikeService = LikeServiceDep,
) -> LikeStatsResponse:
    """Получить статистику оценок фильма."""
    stats = await like_service.get_movie_stats(movie_id)
    return LikeStatsResponse(**stats)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить оценку",
    description="Удалить оценку для фильма",
)
@limiter.limit(settings.LIKES_RATE_LIMIT)
async def delete_like(
    request: Request,
    user_id: CurrentUserDep,
    movie_id: UUID = Path(..., description="UUID фильма"),
    like_service: LikeService = LikeServiceDep,
) -> None:
    """Удалить оценку."""
    deleted = await like_service.delete_like(user_id, movie_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Like not found",
        )
