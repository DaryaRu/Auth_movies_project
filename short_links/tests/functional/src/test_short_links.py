"""Функциональные тесты эндпоинтов коротких ссылок."""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from uuid import uuid4

import pytest
from aiohttp import ClientSession

from tests.functional.utils.check_methods import (
    assert_status_return_json,
)
from tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestShortLinks:
    """Тесты эндпоинтов коротких ссылок."""

    URL = f"{test_settings.api_prefix}/short-links/"

    async def test_create_short_link_success(
        self,
        http_client: ClientSession,
    ):
        """Позитивный тест создания короткой ссылки."""
        user_id = uuid4()
        payload = {
            "user_id": str(user_id),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "redirect_url": "http://localhost/",
        }

        response = await http_client.post(self.URL, json=payload)
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data is not None and isinstance(data, dict)
        assert "short_key" in data
        assert "short_link" in data
        assert "expires_at" in data
        assert len(data["short_key"]) == 8

    async def test_resolve_short_link_not_found(
        self,
        http_client: ClientSession,
    ):
        """Негативный тест: переход по несуществующей короткой ссылке."""
        fake_key = "nonexistent"

        response = await http_client.get(
            f"{test_settings.api_prefix}/resolve/{fake_key}",
        )
        assert response.status == HTTPStatus.NOT_FOUND