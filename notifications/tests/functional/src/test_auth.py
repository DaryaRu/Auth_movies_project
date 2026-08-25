"""Проверка защиты эндпоинтов."""

from http import HTTPStatus
from uuid import uuid4

import aiohttp
import pytest
from settings import test_settings
from utils.check_methods import assert_status

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEMPLATES_URL = f"{test_settings.api_v1_prefix}/notifications/templates/"
MAILINGS_URL = f"{test_settings.api_v1_prefix}/admin-mailings/"
NOTIFICATIONS_URL = f"{test_settings.api_v1_prefix}/notifications/"


async def _no_auth_client():
    return aiohttp.ClientSession(
        base_url=test_settings.api_url,
        connector=aiohttp.TCPConnector(use_dns_cache=False, limit=0),
        cookie_jar=aiohttp.DummyCookieJar(),
        timeout=aiohttp.ClientTimeout(total=None),
        headers={"X-Request-Id": str(uuid4())},
    )


class TestTemplatesStaffAuth:
    """CRUD-эндпоинты шаблонов требуют JWT суперпользователя (StaffUserDep)."""

    async def test_list_without_token_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.get(TEMPLATES_URL)
            await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_list_with_regular_user_returns_403(
        self, regular_user_token: str
    ):
        async with await _no_auth_client() as client:
            response = await client.get(
                TEMPLATES_URL,
                headers={"Authorization": f"Bearer {regular_user_token}"},
            )
            await assert_status(response, HTTPStatus.FORBIDDEN)

    async def test_create_without_token_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.post(
                TEMPLATES_URL,
                json={
                    "code": f"functest_{uuid4().hex[:12]}",
                    "name": "test",
                    "channel": "email",
                    "subject": "test",
                    "body": "test",
                    "allowed_variables": [],
                    "is_active": True,
                },
            )
            await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_get_by_id_with_regular_user_returns_403(
        self, regular_user_token: str
    ):
        async with await _no_auth_client() as client:
            response = await client.get(
                f"{TEMPLATES_URL}{uuid4()}/",
                headers={"Authorization": f"Bearer {regular_user_token}"},
            )
            await assert_status(response, HTTPStatus.FORBIDDEN)


class TestAdminMailingsStaffAuth:
    """GET-эндпоинты рассылок требуют JWT суперпользователя (StaffUserDep)."""

    async def test_list_without_token_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.get(MAILINGS_URL)
            await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_list_with_regular_user_returns_403(
        self, regular_user_token: str
    ):
        async with await _no_auth_client() as client:
            response = await client.get(
                MAILINGS_URL,
                headers={"Authorization": f"Bearer {regular_user_token}"},
            )
            await assert_status(response, HTTPStatus.FORBIDDEN)

    async def test_get_by_id_without_token_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.get(f"{MAILINGS_URL}{uuid4()}/")
            await assert_status(response, HTTPStatus.UNAUTHORIZED)


class TestNotificationsInternalAuth:
    """POST-эндпоинт персонального уведомления требует X-Internal-Secret."""

    async def test_create_without_secret_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.post(
                NOTIFICATIONS_URL,
                json={
                    "user_id": str(uuid4()),
                    "template_id": str(uuid4()),
                    "payload": {},
                },
            )
            await assert_status(response, HTTPStatus.UNAUTHORIZED)

    async def test_create_with_wrong_secret_returns_401(self):
        async with await _no_auth_client() as client:
            response = await client.post(
                NOTIFICATIONS_URL,
                headers={"X-Internal-Secret": "wrong-secret"},
                json={
                    "user_id": str(uuid4()),
                    "template_id": str(uuid4()),
                    "payload": {},
                },
            )
            await assert_status(response, HTTPStatus.UNAUTHORIZED)
