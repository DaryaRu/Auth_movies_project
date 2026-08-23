from http import HTTPStatus

import pytest
from aiohttp import ClientSession
from utils.check_methods import assert_status

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestHealth:
    """Минимальная проверка сервиса."""

    async def test_health_endpoint_returns_ok(
        self, http_client: ClientSession
    ):
        """GET /health отвечает 200, сервис принимает запросы."""
        response = await http_client.get("/health")
        await assert_status(response, HTTPStatus.OK)
