"""API endpoints для рецензий."""

from http import HTTPStatus
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.v1.dependencies import RequiredTokenPayloadDep
from src.core.config import settings
from src.repositories.review_likes import ReviewLikeRepository
from src.repositories.reviews import (
    ReviewRepository,
    ReviewSortField,
    ReviewSortOrder,
)
from src.schemas.reviews import (
    ReviewCreate,
    ReviewResponse,
    ReviewsListResponse,
    ReviewUpdate,
)
from src.services.review_likes import ReviewLikeService
from src.services.reviews import ReviewService


class PaginationParams:
    """Параметры пагинации для endpoints."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Номер страницы"),
        page_size: int = Query(
            default=settings.PAGINATION_DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.PAGINATION_MAX_PAGE_SIZE,
            description="Количество элементов на странице",
        ),
    ):
        self.page = page
        self.page_size = page_size


router = APIRouter(prefix="/reviews", tags=["reviews"])
limiter = Limiter(key_func=get_remote_address)


def get_review_service() -> ReviewService:
    """Получить сервис рецензий."""
    repository = ReviewRepository()
    return ReviewService(repository)


def get_review_like_service() -> ReviewLikeService:
    """Получить сервис лайков рецензий."""
    repository = ReviewLikeRepository()
    return ReviewLikeService(repository)


ReviewServiceDep = Depends(get_review_service)
ReviewLikeServiceDep = Depends(get_review_like_service)

SortByQuery = Annotated[
    Literal["created_at", "rating", "likes", "score"],
    Query(description="Поле для сортировки: created_at (дата), rating (оценка), likes (количество лайков), score (разница лайков и дизлайков)")
]
SortOrderQuery = Annotated[
    Literal["ASC", "DESC"],
    Query(description="Порядок сортировки: ASC (возрастание), DESC (убывание)")
]


@router.post(
    "/",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать рецензию",
    description="""Создать рецензию на фильм. У пользователя может быть только одна рецензия на фильм.
    
    Рецензия состоит из трёх составляющих:
    - **Текст рецензии** — пользовательское мнение о фильме (от 10 до 5000 символов)
    - **Оценка фильма (rating)** — числовая оценка от 1 до 10, где:
      - `1` — минимальная оценка (фильм очень не понравился)
      - `10` — максимальная оценка (фильм очень понравился)
    - **Дополнительные данные** — дата публикации, автор (user_id) — добавляются автоматически
    
    После публикации рецензии другие пользователи могут голосовать за неё (лайк/дизлайк).
    """,
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def create_review(
    request: Request,
    review_data: ReviewCreate,
    user_id: RequiredTokenPayloadDep,
    review_service: ReviewService = ReviewServiceDep,
) -> ReviewResponse:
    """Создать рецензию."""
    try:
        result = await review_service.create_review(
            user_id, review_data.movie_id, review_data.text, review_data.rating
        )
        return ReviewResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=str(e),
        )


@router.get(
    "/my",
    response_model=ReviewsListResponse,
    summary="Мои рецензии",
    description="Получить список рецензий текущего пользователя с возможностью сортировки",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def get_my_reviews(
    request: Request,
    user_id: RequiredTokenPayloadDep,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    sort_by: Annotated[ReviewSortField, SortByQuery],
    sort_order: Annotated[ReviewSortOrder, SortOrderQuery],
    review_service: ReviewService = ReviewServiceDep,
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> ReviewsListResponse:
    """Получить мои рецензии с сортировкой."""
    result = await review_service.get_user_reviews(
        user_id,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    review_ids = [item["id"] for item in result["items"]]
    likes_stats = await review_like_service.get_reviews_stats(review_ids)
    
    items_with_stats = []
    for item in result["items"]:
        review_id = item["id"]
        stats = likes_stats.get(review_id, {"likes": 0, "dislikes": 0, "total": 0, "score": 0})
        items_with_stats.append({
            **item,
            "likes_count": stats["likes"],
            "dislikes_count": stats["dislikes"],
            "score": stats["score"],
        })
    
    return ReviewsListResponse(
        items=[ReviewResponse(**item) for item in items_with_stats],
        total=result["total"],
        page=result["page"],
        page_size=pagination.page_size,
    )


@router.get(
    "/movie/{movie_id}",
    response_model=ReviewsListResponse,
    summary="Рецензии фильма",
    description="""Получить список рецензий для конкретного фильма с возможностью гибкой сортировки.
    
    Доступные варианты сортировки:
    - `created_at` — по дате публикации (ASC/DESC)
    - `rating` — по оценке фильма пользователем (ASC/DESC)
    - `likes` — по количеству лайков рецензии (ASC/DESC)
    - `score` — по разнице лайков и дизлайков (ASC/DESC)
    
    Параметры сортировки передаются через query-параметры `sort_by` и `sort_order`.
    """,
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def get_movie_reviews(
    request: Request,
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    movie_id: UUID = Path(..., description="UUID фильма"),
    sort_by: ReviewSortField = SortByQuery,
    sort_order: ReviewSortOrder = SortOrderQuery,
    review_service: ReviewService = ReviewServiceDep,
    review_like_service: ReviewLikeService = ReviewLikeServiceDep,
) -> ReviewsListResponse:
    """Получить рецензии фильма с сортировкой."""
    result = await review_service.get_movie_reviews(
        movie_id,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    # Добавляем статистику лайков к каждой рецензии
    review_ids = [UUID(item["id"]) for item in result["items"]]
    likes_stats = await review_like_service.get_reviews_stats(review_ids)
    
    items_with_stats = []
    for item in result["items"]:
        review_id = UUID(item["id"])
        stats = likes_stats.get(review_id, {"likes": 0, "dislikes": 0, "total": 0, "score": 0})
        items_with_stats.append({
            **item,
            "likes_count": stats["likes"],
            "dislikes_count": stats["dislikes"],
            "score": stats["score"],
        })
    
    return ReviewsListResponse(
        items=[ReviewResponse(**item) for item in items_with_stats],
        total=result["total"],
        page=result["page"],
        page_size=pagination.page_size,
    )


@router.get(
    "/movie/{movie_id}/stats",
    summary="Статистика рецензий фильма",
    description="Получить статистику рецензий для фильма (средний рейтинг и количество)",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def get_movie_stats(
    request: Request,
    movie_id: UUID = Path(..., description="UUID фильма"),
    review_service: ReviewService = ReviewServiceDep,
) -> dict:
    """Получить статистику рецензий фильма."""
    return await review_service.get_movie_stats(movie_id)


@router.patch(
    "/{movie_id}",
    response_model=ReviewResponse,
    summary="Обновить рецензию",
    description="Обновить рецензию на фильм",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def update_review(
    request: Request,
    user_id: RequiredTokenPayloadDep,
    movie_id: UUID = Path(..., description="UUID фильма"),
    review_data: ReviewUpdate | None = None,
    review_service: ReviewService = ReviewServiceDep,
) -> ReviewResponse:
    """Обновить рецензию."""
    if review_data is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No data provided for update",
        )
    result = await review_service.update_review(
        user_id, movie_id, text=review_data.text, rating=review_data.rating
    )
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Review not found",
        )
    return ReviewResponse(**result)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить рецензию",
    description="Удалить рецензию на фильм",
)
@limiter.limit(settings.REVIEWS_RATE_LIMIT)
async def delete_review(
    request: Request,
    user_id: RequiredTokenPayloadDep,
    movie_id: UUID = Path(..., description="UUID фильма"),
    review_service: ReviewService = ReviewServiceDep,
) -> None:
    """Удалить рецензию."""
    deleted = await review_service.delete_review(user_id, movie_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Review not found",
        )
