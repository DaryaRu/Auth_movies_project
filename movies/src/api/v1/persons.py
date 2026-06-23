"""Persons API endpoint router.

Provides routes for full-text person search, paginated listing,
fetching person details, and retrieving films associated with a person.
"""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi_cache.decorator import cache

from api.v1.dependencies import PaginationDepend
from core import config
from schemas.film_shorts import FilmShortResponse as FilmShort
from schemas.persons import Person
from dependencies import get_person_service
from services.persons import PersonService

router = APIRouter()


@router.get(
    "/search",
    response_model=list[Person],
    summary="Полнотекстовый поиск по персонам",
    description=(
        "Полнотекстовый поиск по именам (актеров, режиссеров, сценаристов). "
        "Используйте параметры page_number для выбора страницы и "
        "page_size для ограничения количества элементов."
    ),
    response_description="Список найденных персон с их данными по фильмам",
)
@cache(expire=config.CACHE_EXPIRE)
async def person_search(
    pagination: PaginationDepend,
    person_service: PersonService = Depends(get_person_service),
    query: str = Query(..., description="Имя или часть имени для поиска"),
) -> list[Person]:
    """Perform a full-text search for persons by name."""
    return await person_service.search(
        query=query,
        page_number=pagination.page_number,
        page_size=pagination.page_size,
    )


@router.get(
    "/{person_uuid}/",
    response_model=Person,
    summary="Получить персону по UUID",
    description=(
        "Получить детальную информацию о конкретной "
        "персоне по ее уникальному идентификатору (UUID)."
    ),
    response_description=(
        "Детальная информация о персоне, включая ее имя и данные по фильму"
    ),
    responses={
        HTTPStatus.NOT_FOUND: {
            "description": "Персона с таким UUID не найдена"
        }
    },
)
@cache(expire=config.CACHE_EXPIRE)
async def person_details(
    person_uuid: UUID = Path(
        ...,
        description="Уникальный идентификатор персоны (UUID)",
    ),
    person_service: PersonService = Depends(get_person_service),
) -> Person:
    """Get detailed information for a specific person by their UUID."""
    person = await person_service.get_by_uuid(person_uuid)
    if not person:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="person not found"
        )
    return person


@router.get(
    "/{person_uuid}/film",
    response_model=list[FilmShort],
    summary="Получить все фильмы заданной персоны",
    description=(
        "Получить список всех кинопроизведений, "
        "в создании которых принимала участие данная персона. "
        "Используйте параметры page_number для выбора страницы и "
        "page_size для ограничения количества элементов."
    ),
    response_description="Список фильмов с их названиями и рейтингами",
)
@cache(expire=config.CACHE_EXPIRE)
async def person_films(
    pagination: PaginationDepend,
    person_uuid: UUID = Path(
        ...,
        description="Уникальный идентификатор персоны (UUID)",
    ),
    person_service: PersonService = Depends(get_person_service),
) -> list[FilmShort]:
    """Get all films associated with a specific person."""
    films = await person_service.get_person_films(
        person_uuid,
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )
    if films is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="person not found"
        )
    return [FilmShort.model_validate(f.model_dump()) for f in films]


@router.get(
    "/",
    response_model=list[Person],
    summary="Получить список всех персон",
    description=(
        "Получить полный список персон с пагинацией. "
        "Используйте параметры page_number для выбора страницы и "
        "page_size для ограничения количества элементов."
    ),
    response_description="Список всех персон в системе",
)
@cache(expire=config.CACHE_EXPIRE)
async def person_list(
    pagination: PaginationDepend,
    person_service: PersonService = Depends(get_person_service),
) -> list[Person]:
    """Get a paginated list of all persons."""
    return await person_service.get_list(
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )
