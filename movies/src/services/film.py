"""Film service: business logic for films."""

from uuid import UUID

from exceptions import ObjectNotFoundException
from models.films import Film, FilmShort
from repositories.films import AbstractFilmRepository


class FilmService:
    def __init__(self, repository: AbstractFilmRepository):
        """Initialize service with film repository."""
        self.film_repo = repository

    async def get_by_uuid(self, film_id: UUID) -> Film | None:
        """Return a film by id."""
        try:
            data = await self.film_repo.get_by_id(str(film_id))
        except ObjectNotFoundException:
            return None
        return Film(**data)

    async def get_list(
        self,
        sort: str | None,
        genre: UUID | None,
        page_number: int,
        page_size: int,
    ) -> list[FilmShort]:
        """Return a paginated list of films (with sort and genre filter)."""
        data = await self.film_repo.get_list(
            sort=sort,
            genre=genre,
            page_number=page_number,
            page_size=page_size,
        )
        return [FilmShort(**item) for item in data]

    async def search(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[FilmShort]:
        """Search films by query string for title and description fields."""
        data = await self.film_repo.search_films(
            query_str=query,
            page_number=page_number,
            page_size=page_size,
        )
        return [FilmShort(**item) for item in data]
