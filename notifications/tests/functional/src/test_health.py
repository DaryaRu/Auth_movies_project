from http import HTTPStatus

import pytest
from aiohttp import ClientSession
from settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestHealth:
    async def test_health_endpoint_returns_ok(
        self, http_client: ClientSession
    ):
        response = await http_client.get("/health")
        assert response.status == HTTPStatus.OK

    async def test_templates_list_endpoint_is_reachable(
        self, http_client: ClientSession
    ):
        response = await http_client.get(
            f"{test_settings.api_v1_prefix}/notifications/templates/"
        )
        assert response.status == HTTPStatus.OK
        data = await response.json()
        assert isinstance(data, list)
