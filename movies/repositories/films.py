"""Film repository."""

from abc import abstractmethod
from uuid import UUID

from repositories.base import BaseElasticRepository
from utils.parsers import parse_sort_param


class AbstractFilmRepository(BaseElasticRepository):
    """Abstract contract for film repositories."""

    @abstractmethod
    async def search_films(
        self,
        query_str: str,
        page_number: int,
        page_size: int,
    ) -> list[dict]: ...

    @abstractmethod
    async def get_list(
        self,
        page_number: int,
        page_size: int,
        sort: str | None,
        genre: UUID | None,
    ) -> list[dict]: ...

    @abstractmethod
    async def get_films_by_person(
        self,
        person_id: UUID,
        page_number: int,
        page_size: int,
    ) -> list[dict]: ...


class FilmRepository(AbstractFilmRepository):
    """Elasticsearch repository for film documents."""

    async def search_films(
        self,
        query_str: str,
        page_number: int,
        page_size: int,
    ) -> list[dict]:
        """Search films by query string across title and description fields."""
        query = {
            "multi_match": {
                "query": query_str,
                "fields": ["title", "description"],
            }
        }
        return await self.get_filtered(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

    async def get_list(
        self,
        page_number: int,
        page_size: int,
        sort: str | None = None,
        genre: UUID | None = None,
    ) -> list[dict]:
        """Return paginated films with sort and genre filter."""
        query: dict | None = None
        if genre:
            query = {
                "nested": {
                    "path": "genres",
                    "query": {"term": {"genres.id": str(genre)}},
                }
            }

        sort_param: dict | None = None
        if sort:
            field, order = parse_sort_param(sort)
            sort_param = {field: {"order": order}}

        return await self.get_filtered(
            query=query,
            sort=sort_param,
            page_number=page_number,
            page_size=page_size,
        )

    async def get_films_by_person(
        self,
        person_id: UUID,
        page_number: int,
        page_size: int,
    ) -> list[dict]:
        """Return films where person is an actor, writer or director."""
        pid = str(person_id)
        query = {
            "bool": {
                "should": [
                    {
                        "nested": {
                            "path": "actors",
                            "query": {"term": {"actors.id": pid}},
                        }
                    },
                    {
                        "nested": {
                            "path": "writers",
                            "query": {"term": {"writers.id": pid}},
                        }
                    },
                    {
                        "nested": {
                            "path": "directors",
                            "query": {"term": {"directors.id": pid}},
                        }
                    },
                ]
            }
        }
        return await self.get_filtered(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )
