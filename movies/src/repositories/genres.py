"""Genres repository."""

from abc import abstractmethod

from repositories.base import BaseElasticRepository
from utils.parsers import parse_sort_param


class AbstractGenreRepository(BaseElasticRepository):
    """Abstract contract for genre repositories."""

    @abstractmethod
    async def get_sorted_genres(
        self,
        page_number: int,
        page_size: int,
        sort_str: str | None,
    ) -> list[dict]: ...


class GenresRepository(AbstractGenreRepository):
    """Elasticsearch repository for genre documents."""

    async def get_sorted_genres(
        self,
        page_number: int,
        page_size: int,
        sort_str: str | None = None,
    ) -> list[dict]:
        """Return a paginated and sorted list of genre documents."""
        if sort_str:
            field, order = parse_sort_param(sort_str)
            field = "name.raw" if field == "name" else field
            sort = {field: order}
        else:
            sort = {"name.raw": "asc"}

        return await self.get_filtered(
            page_number=page_number,
            page_size=page_size,
            query={"match_all": {}},
            sort=sort,
        )
