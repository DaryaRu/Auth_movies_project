"""Film endpoints."""

from http import HTTPStatus
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_cache.decorator import cache

from api.v1.dependencies import PaginationDepend
from core import config
from schemas.film_shorts import FilmShortResponse
from schemas.films import FilmResponse
from dependencies import get_film_service
from services.film import FilmService

router = APIRouter()


@router.get(
    "/search",
    response_model=list[FilmShortResponse],
    summary="Полнотекстовый поиск кинопроизведений",
    description="Полнотекстовый поиск по кинопроизведениям",
    response_description="Название и рейтинг фильма",
)
@cache(expire=config.CACHE_EXPIRE)
async def films_search(
    pagination: PaginationDepend,
    film_service: FilmService = Depends(get_film_service),
    query: str = Query(
        ...,
        description=(
            "Текст поискового запроса (слово или часть названия фильма)"
        ),
    ),
) -> list[FilmShortResponse]:
    """Endpoint to search films by query string."""
    films = await film_service.search(
        query, pagination.page_number, pagination.page_size
    )
    return [FilmShortResponse.model_validate(f.model_dump()) for f in films]


@router.get(
    "/{film_id}",
    response_model=FilmResponse,
    summary="Получить кинопроизведение по UUID",
    description="Возвращает полную информацию о кинопроизведении по UUID",
    response_description="Полная информация о фильме",
    responses={
        HTTPStatus.NOT_FOUND: {"description": "Фильм с таким UUID не найден"}
    },
)
@cache(expire=config.CACHE_EXPIRE)
async def film_details(
    film_id: UUID = Path(
        ...,
        description="Уникальный идентификатор фильма (UUID)",
    ),
    film_service: FilmService = Depends(get_film_service),
) -> FilmResponse:
    """Endpoint to return full details for a single film by id."""
    film = await film_service.get_by_uuid(film_id)
    if not film:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="film not found",
        )
    return FilmResponse.model_validate(film.model_dump())


@router.get(
    "/",
    response_model=list[FilmShortResponse],
    summary="Список кинопроизведений",
    description=(
        "Список кинопроизведений с сортировкой и фильтром по жанру. "
        "Используйте параметры page_number для выбора страницы и "
        "page_size для ограничения количества элементов."
    ),
    response_description="Название и рейтинг фильма",
)
@cache(expire=config.CACHE_EXPIRE)
async def films_list(
    pagination: PaginationDepend,
    film_service: FilmService = Depends(get_film_service),
    sort: Literal[
        "imdb_rating",
        "-imdb_rating",
    ] | None = Query(
        default=None,
        description=(
            "Поле для сортировки (например, imdb_rating и -imdb_rating). "
            "Знак минус (-) "
            "означает сортировку по убыванию."
        ),
    ),
    genre: Optional[UUID] = Query(
        default=None,
        alias="filter[genre]",
        description="UUID жанра для фильтрации списка фильмов",
    ),
) -> list[FilmShortResponse]:
    """Endpoint to return a paginated list of films
    with sort and genre filter."""
    films = await film_service.get_list(
        sort, genre, pagination.page_number, pagination.page_size
    )
    return [FilmShortResponse.model_validate(f.model_dump()) for f in films]
