"""Tests for API behaviour when Elasticsearch or Redis is unavailable."""

import pytest
from unittest.mock import AsyncMock, patch

from elastic_transport import ConnectionError as ESConnectionError
from redis.exceptions import RedisError

API_PREFIX = "/api/v1"

FILMS = f"{API_PREFIX}/films/"
GENRES = f"{API_PREFIX}/genres/"
PERSONS = f"{API_PREFIX}/persons/"
FILM_ID = "00000000-0000-0000-0000-000000000001"

ES_LIST = "repositories.base.BaseElasticRepository.get_filtered"
ES_DETAIL = "repositories.base.BaseElasticRepository.get_by_id"
REDIS_GET_WITH_TTL = "fastapi_cache.backends.redis.RedisBackend.get_with_ttl"


class TestESUnavailable:
    """All endpoints return 503 when ES raises ConnectionError."""

    @pytest.mark.parametrize("url", [FILMS, GENRES, PERSONS])
    async def test_list_returns_503(self, http_client, url: str):
        with patch(
            ES_LIST,
            new=AsyncMock(side_effect=ESConnectionError("ES down")),
        ):
            r = await http_client.get(url)
            assert r.status_code == 503

    async def test_detail_returns_503(self, http_client):
        with patch(
            ES_DETAIL,
            new=AsyncMock(side_effect=ESConnectionError("ES down")),
        ):
            r = await http_client.get(f"{API_PREFIX}/films/{FILM_ID}")
            assert r.status_code == 503


class TestRedisUnavailable:
    """Redis down: graceful degradation — API still returns 200."""

    async def test_film_list_when_redis_down(self, http_client):
        with (
            patch(
                REDIS_GET_WITH_TTL,
                new=AsyncMock(side_effect=RedisError("Redis down")),
            ),
            patch(
                ES_LIST,
                new=AsyncMock(return_value=[]),
            ),
        ):
            r = await http_client.get(FILMS)
            assert r.status_code == 200
            assert isinstance(r.json(), list)
