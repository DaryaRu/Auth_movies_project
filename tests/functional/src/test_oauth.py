"""Функциональные тесты OAuth-эндпоинтов."""

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import pytest
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

PROVIDERS = {
    "google": "https://accounts.google.com/o/oauth2/auth",
    "yandex": "https://oauth.yandex.ru/authorize",
}


class TestOAuthRedirect:
    """Тесты эндпоинта GET /auth/{provider}/."""

    UNKNOWN_URL = f"{test_settings.api_prefix}/auth/unknown_provider/"

    @pytest.mark.parametrize("provider", PROVIDERS)
    async def test_redirect_returns_200(
        self, http_client: ClientSession, provider: str
    ):
        """GET /auth/{provider}/ возвращает 200 с URL авторизации."""
        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/"
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert "url" in data

    @pytest.mark.parametrize("provider", PROVIDERS)
    async def test_redirect_stores_state_in_redis(
        self, http_client: ClientSession, redis_client, provider: str
    ):
        """GET /auth/{provider}/ сохраняет state в Redis с ключом oauth_state:{state}."""
        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/"
        )
        data = await response.json()

        parsed = urlparse(data["url"])
        state = parse_qs(parsed.query)["state"][0]

        stored = await redis_client.get(f"oauth_state:{state}")
        assert stored is not None
        assert stored == provider

    @pytest.mark.parametrize("provider,expected_url", PROVIDERS.items())
    async def test_redirect_url_points_to_provider(
        self, http_client: ClientSession, provider: str, expected_url: str
    ):
        """Возвращённый URL ведёт на страницу авторизации провайдера."""
        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/"
        )
        data = await response.json()

        assert data["url"].startswith(expected_url)

    @pytest.mark.parametrize("provider", PROVIDERS)
    async def test_redirect_url_contains_required_params(
        self, http_client: ClientSession, provider: str
    ):
        """Возвращённый URL содержит обязательные OAuth-параметры."""
        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/"
        )
        data = await response.json()
        url = data["url"]

        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "state=" in url

    async def test_unknown_provider_returns_422(
        self, http_client: ClientSession
    ):
        """Запрос к несуществующему провайдеру возвращает 422."""
        response = await http_client.get(self.UNKNOWN_URL)

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY


class TestOAuthCallback:
    """Тесты эндпоинта GET /auth/{provider}/callback/."""

    UNKNOWN_CALLBACK_URL = (
        f"{test_settings.api_prefix}/auth/unknown_provider/callback/"
    )

    @pytest.mark.parametrize("provider", PROVIDERS)
    async def test_callback_invalid_state_returns_400(
        self, http_client: ClientSession, provider: str
    ):
        """State, отсутствующий в Redis, возвращает 400."""
        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/callback/",
            params={"code": "some-code", "state": "some-state"},
        )
        data = await assert_status_return_json(
            response, HTTPStatus.BAD_REQUEST
        )

        assert_error_detail(data)

    async def test_callback_unknown_provider_returns_422(
        self, http_client: ClientSession
    ):
        """Callback к несуществующему провайдеру возвращает 422."""
        response = await http_client.get(
            self.UNKNOWN_CALLBACK_URL,
            params={"code": "some-code", "state": "some-state"},
        )

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("provider", PROVIDERS)
    async def test_callback_valid_state_proceeds_to_code_exchange(
        self, http_client: ClientSession, provider: str
    ):
        """Передается корректный state, валидация проходит и сервис переходит к обмену code на токен.
        Проверяется, что обмен фейкового кода с провайдером завершается ошибкой провайдера 502,
        а не ошибкой state 400.
        """
        redirect_response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/",
        )
        data = await redirect_response.json()

        parsed = urlparse(data["url"])
        state = parse_qs(parsed.query)["state"][0]

        response = await http_client.get(
            f"{test_settings.api_prefix}/auth/{provider}/callback/",
            params={"code": "some-code", "state": state},
        )

        assert response.status == HTTPStatus.BAD_GATEWAY
