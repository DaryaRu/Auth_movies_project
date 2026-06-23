"""Base Elasticsearch repository."""

import socket
from abc import ABC
from urllib3.exceptions import NameResolutionError

from elasticsearch import AsyncElasticsearch, BadRequestError, NotFoundError
from elastic_transport import ConnectionTimeout, ConnectionError

from exceptions import ObjectNotFoundException
from utils.decorators import backoff


class BaseElasticRepository(ABC):
    """Base repository for Elasticsearch operations."""

    def __init__(self, elastic_client: AsyncElasticsearch, index: str):
        """Initialize with an Elasticsearch client and index name."""
        self.elastic_client = elastic_client
        self.index = index

    @backoff(
        start_sleep_time=1,
        factor=2,
        border_sleep_time=10,
        exceptions=(
            ConnectionError,
            ConnectionTimeout,
            NameResolutionError,
            socket.gaierror,
        ),
    )
    async def get_by_id(
        self,
        entity_id: str,
        source: list[str] | None = None,
    ) -> dict:
        """Fetch a single document by id."""
        try:
            doc = await self.elastic_client.get(
                index=self.index,
                id=entity_id,
                source_includes=source,
            )
        except NotFoundError as ex:
            raise ObjectNotFoundException from ex
        return doc["_source"]

    @backoff(
        start_sleep_time=1,
        factor=2,
        border_sleep_time=10,
        exceptions=(
            ConnectionError,
            ConnectionTimeout,
            NameResolutionError,
            socket.gaierror,
        ),
    )
    async def get_filtered(
        self,
        page_size: int | None = None,
        page_number: int | None = None,
        query: dict | None = None,
        sort: dict | None = None,
        source: list[str] | None = None,
    ) -> list[dict]:
        """Search documents with optional query, sort, and pagination."""
        body = {
            "query": query or {"match_all": {}},
        }
        if source:
            body["_source"] = source
        if page_size and page_number:
            body["from"] = (page_number - 1) * page_size
            body["size"] = page_size

        if sort:
            body["sort"] = [sort]

        try:
            result = await self.elastic_client.search(
                index=self.index,
                body=body,
            )
        except (BadRequestError, NotFoundError):
            return []

        return [hit["_source"] for hit in result["hits"]["hits"]]
