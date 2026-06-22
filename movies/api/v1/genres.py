"""Genres API endpoint router.

Provides routes for paginated genre listing, sorting,
and fetching specific genre details by unique identifier.
"""

from http import HTTPStatus
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_cache.decorator import cache

from api.v1.dependencies import PaginationDepend
from core import config
from schemas.genres import GenreResponse as Genre
from dependencies import get_genre_service
from services.genres import GenreService

router = APIRouter()


@router.get(
    "/",
    response_model=list[Genre],
    summary="Список всех жанров",
    description=(
        "Получить список жанров с пагинацией и сортировкой. "
        "Используйте параметры page_number для выбора страницы и "
        "page_size для ограничения количества элементов."
    ),
    response_description="Список жанров с их идентификаторами и названиями",
)
@cache(expire=config.CACHE_EXPIRE)
async def genre_list(
    pagination: PaginationDepend,
    genre_service: GenreService = Depends(get_genre_service),
    sort: Literal["name", "-name"] | None = Query(
        None,
        description=(
            "Сортировка по имени по алфавиту (name или -name). "
            "Знак минус (-) означает сортировку по убыванию."
        ),
    ),
) -> list[Genre]:
    """Get a paginated list of genres with optional sorting."""
    return await genre_service.get_list(
        page_size=pagination.page_size,
        page_number=pagination.page_number,
        sort=sort,
    )


@router.get(
    "/{genre_uuid}",
    response_model=Genre,
    summary="Получить жанр по UUID",
    description=(
        "Получить детальную информацию о конкретном "
        "жанре по его уникальному идентификатору (UUID)."
    ),
    response_description="Детальная информация о жанре",
    responses={
        HTTPStatus.NOT_FOUND: {"description": "Жанр с таким UUID не найден"}
    },
)
@cache(expire=config.CACHE_EXPIRE)
async def genre_details(
    genre_uuid: UUID = Path(
        ...,
        description="Уникальный идентификатор жанра (UUID)",
    ),
    genre_service: GenreService = Depends(get_genre_service),
) -> Genre:
    """Get detailed information for a specific genre by its UUID."""
    genre = await genre_service.get_by_uuid(genre_uuid)
    if not genre:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="genre not found"
        )
    return genre
