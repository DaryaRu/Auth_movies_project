"""Load documents into Elasticsearch."""

import logging
from typing import Any, Protocol
from uuid import UUID

from backoff import backoff
from config import Settings
from elasticsearch import Elasticsearch, helpers

logger = logging.getLogger(__name__)


class IndexableDocument(Protocol):
    """Structural type for pydantic models indexable into Elasticsearch."""

    id: UUID

    def model_dump(self, *, mode: str = ...) -> dict[str, Any]: ...


class ElasticsearchWriter:
    """Write ETL documents to Elasticsearch."""

    def __init__(self, settings: Settings) -> None:
        """Initialize writer with a Elasticsearch client."""
        self.settings = settings
        self.client = Elasticsearch(hosts=[f"http://{settings.elastic_host}:{settings.elastic_port}"])

    @backoff()
    def check_or_create_index(
        self,
        index: str,
        schema: dict,
    ) -> None:
        """Create index with given schema if it does not exist."""
        if self.client.indices.exists(index=index):
            logger.info(
                "Elasticsearch index %s already exists",
                index,
            )
            return

        self.client.indices.create(
            index=index,
            body=schema,
        )

        logger.info(
            "Created Elasticsearch index %s",
            index,
        )

    @backoff()
    def bulk_save(
        self,
        index: str,
        documents: list[IndexableDocument],
    ) -> None:
        """Index documents batch into Elasticsearch."""
        if not documents:
            return

        actions = [
            {
                "_index": index,
                "_id": str(document.id),
                "_source": document.model_dump(mode="json"),
            }
            for document in documents
        ]

        helpers.bulk(self.client, actions)

        logger.info(
            "Uploaded %s documents to index %s",
            len(documents),
            index,
        )
