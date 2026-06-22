"""Utility functions for Elasticsearch indexes."""

import logging

import pytest
from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

logger = logging.getLogger(__name__)


async def create_index(
    es_client: AsyncElasticsearch, index: str, schema: dict
) -> None:
    """Delete index if exists and then create fresh index."""
    await delete_index(es_client, index)
    await es_client.indices.create(
        index=index,
        settings=schema.get("settings"),
        mappings=schema.get("mappings"),
    )


async def delete_index(es_client: AsyncElasticsearch, index: str) -> None:
    """Delete ES index (skip if it does not exist)."""
    try:
        await es_client.indices.delete(index=index)
    except NotFoundError:
        pass


async def load_data(
    es_client: AsyncElasticsearch, index: str, data: list[dict]
) -> None:
    """Bulk-load documents into index and refresh."""
    updated, errors = await async_bulk(
        es_client,
        [{"_index": index, "_id": doc["id"], **doc} for doc in data],
        refresh=True,
    )
    if errors:
        pytest.fail(
            f"Failed to index {len(errors)} document(s) into '{index}': "
            f"{errors}"
        )
    logger.info("Successfully indexed %d documents into '%s'", updated, index)
