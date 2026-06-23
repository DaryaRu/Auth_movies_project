"""Person business logic service module."""

from uuid import UUID

from exceptions import ObjectNotFoundException
from models.films import FilmShort
from models.persons import Person as PersonModel
from repositories.films import AbstractFilmRepository
from repositories.persons import AbstractPersonRepository


class PersonService:
    """Service class for managing person-related business logic."""

    def __init__(
        self,
        person_repo: AbstractPersonRepository,
        movie_repo: AbstractFilmRepository,
    ):
        """Initialize service with specialized repositories."""
        self.person_repo = person_repo
        self.movie_repo = movie_repo

    async def get_by_uuid(self, person_uuid: UUID) -> PersonModel | None:
        """Get person details by their unique identifier."""
        try:
            doc_source = await self.person_repo.get_by_id(str(person_uuid))
            return PersonModel(**doc_source)
        except ObjectNotFoundException:
            return None

    async def get_list(
        self,
        page_size: int,
        page_number: int,
    ) -> list[PersonModel]:
        """Get a paginated list of persons."""
        docs_sources = await self.person_repo.get_filtered(
            page_size=page_size,
            page_number=page_number,
        )
        return [PersonModel(**source) for source in docs_sources]

    async def search(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[PersonModel]:
        """Search persons by name."""
        docs_sources = await self.person_repo.search_persons(
            query_str=query, page_number=page_number, page_size=page_size
        )
        return [PersonModel(**source) for source in docs_sources]

    async def get_person_films(
        self,
        person_uuid: UUID,
        page_size: int,
        page_number: int,
    ) -> list[FilmShort] | None:
        """Get all films associated with a specific person."""
        person = await self.get_by_uuid(person_uuid)
        if not person:
            return None

        movies_sources = await self.movie_repo.get_films_by_person(
            person_id=person_uuid,
            page_size=page_size,
            page_number=page_number,
        )
        return [FilmShort(**source) for source in movies_sources]
