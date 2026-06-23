"""Persons repository."""

from abc import abstractmethod

from repositories.base import BaseElasticRepository


class AbstractPersonRepository(BaseElasticRepository):
    """Abstract contract for person repositories."""

    @abstractmethod
    async def search_persons(
        self,
        query_str: str,
        page_number: int,
        page_size: int,
    ) -> list[dict]: ...


class PersonsRepository(AbstractPersonRepository):
    """Elasticsearch repository for person documents."""

    async def search_persons(
        self,
        query_str: str,
        page_number: int,
        page_size: int,
    ) -> list[dict]:
        """Search persons by name with fuzzy matching."""
        query = {"match": {"name": {"query": query_str, "fuzziness": "AUTO"}}}
        return await self.get_filtered(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )
