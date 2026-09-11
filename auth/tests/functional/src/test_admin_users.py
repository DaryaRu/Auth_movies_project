"""Функциональные тесты профилей в админке
(GET /admin/users/, GET /admin/users/{user_id}/)."""

import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_error_detail,
    assert_status_return_json,
)
from functional.utils.helpers import hash_password

pytestmark = pytest.mark.asyncio(loop_scope="session")

ADMIN_USERS_URL = f"{test_settings.api_prefix}/admin/users"
ROLES_URL = f"{test_settings.api_prefix}/roles"
PERMISSIONS_URL = f"{test_settings.api_prefix}/permissions"
NOT_EXISTING_UUID = uuid.uuid4()

UNIQUE_TEST_MARKER = f"admin_search{uuid.uuid4().hex[:8]}"

_SEARCHABLE_USERS_FULL_NAMES = (
    "Иванова Эсмиральда",
    "Соколова Ольга",
    "Кузьмина Артемида",
)


@pytest_asyncio.fixture(scope="module")
async def search_and_pagination_users(pg_write_data) -> list[dict[str, Any]]:
    """Создает пользователей для теста поиска и пагинации.

    Маркер уникален (используется в email), чтобы не пересекаться с пользователями
    из других фикстур и тестов. Берем 3 пользователя, чтобы хватило для проверки пагинации.
    """
    users = []
    for i, full_name in enumerate(_SEARCHABLE_USERS_FULL_NAMES):
        data = {
            "id": uuid.uuid4(),
            "email": f"{UNIQUE_TEST_MARKER}_{i}@example.com",
            "phone": None,
            "full_name": full_name,
            "hashed_password": hash_password("password12345"),
            "is_superuser": False,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await pg_write_data("users", tuple(data.keys()), tuple(data.values()))
        users.append(data)
    return users


@pytest_asyncio.fixture(scope="module")
async def view_permission_granted_headers(
    session_http_client: ClientSession,
    superuser_token: str,
    pg_write_data,
) -> AsyncGenerator[dict[str, str], None]:
    """Заголовок Authorization для пользователя с назначенным правом user:view_personal_data."""
    superuser_headers = {"Authorization": f"Bearer {superuser_token}"}

    user_id = uuid.uuid4()
    email = f"view_permission_{uuid.uuid4().hex[:8]}@example.com"
    password = "viewpermission12345"
    await pg_write_data(
        "users",
        (
            "id",
            "email",
            "hashed_password",
            "is_superuser",
            "is_active",
            "created_at",
            "updated_at",
        ),
        (
            user_id,
            email,
            hash_password(password),
            False,
            True,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
        ),
    )
    login_resp = await session_http_client.post(
        f"{test_settings.api_prefix}/login/",
        json={"email": email, "password": password},
    )
    login_data = await login_resp.json()
    user_headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    permission_payload = {
        "code": "user:view_personal_data",
        "name": "Просмотр личных данных пользователей",
        "category": "users",
    }
    permission_resp = await session_http_client.post(
        f"{PERMISSIONS_URL}/",
        json=permission_payload,
        headers=superuser_headers,
    )
    permission = await permission_resp.json()

    role_resp = await session_http_client.post(
        f"{ROLES_URL}/",
        json={
            "name": f"test_view_profiles_{uuid.uuid4().hex[:8]}",
            "description": "Test role",
        },
        headers=superuser_headers,
    )
    role = await role_resp.json()

    await session_http_client.post(
        f"{ROLES_URL}/{role['id']}/permissions/{permission['id']}/",
        headers=superuser_headers,
    )
    await session_http_client.post(
        f"{ROLES_URL}/{role['id']}/users/{user_id}/",
        headers=superuser_headers,
    )

    yield user_headers

    await session_http_client.delete(
        f"{ROLES_URL}/{role['id']}/users/{user_id}/",
        headers=superuser_headers,
    )
    await session_http_client.delete(
        f"{ROLES_URL}/{role['id']}/", headers=superuser_headers
    )
    await session_http_client.delete(
        f"{PERMISSIONS_URL}/{permission['id']}/", headers=superuser_headers
    )


class TestListUsers:
    """Тесты GET /admin/users/."""

    async def test_list_users_search_by_marker(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """Поиск по общей части email находит всех подходящих пользователей."""
        response = await http_client.get(
            ADMIN_USERS_URL + "/",
            params={"search": UNIQUE_TEST_MARKER, "page_size": 50},
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["total"] == len(search_and_pagination_users)
        found_emails = {item["email"] for item in data["items"]}
        assert found_emails == {
            u["email"] for u in search_and_pagination_users
        }

    async def test_list_users_search_by_email(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """Поиск по точному email находит только одного пользователя."""
        target = search_and_pagination_users[0]
        response = await http_client.get(
            ADMIN_USERS_URL + "/",
            params={"search": target["email"]},
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["total"] == 1
        assert data["items"][0]["email"] == target["email"]

    async def test_list_users_search_no_match(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Поиск без совпадений возвращает пустой список."""
        response = await http_client.get(
            ADMIN_USERS_URL + "/",
            params={"search": f"no-such-user-{uuid.uuid4().hex}"},
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_users_pagination(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """page_size ограничивает выдачу, page_number сдвигает окно, total не меняется."""
        first_page = await http_client.get(
            ADMIN_USERS_URL + "/",
            params={
                "search": UNIQUE_TEST_MARKER,
                "page_number": 1,
                "page_size": 2,
            },
            headers=superuser_headers,
        )
        first_data = await assert_status_return_json(first_page, HTTPStatus.OK)
        assert len(first_data["items"]) == 2
        assert first_data["total"] == 3
        assert first_data["page_number"] == 1
        assert first_data["page_size"] == 2

        second_page = await http_client.get(
            ADMIN_USERS_URL + "/",
            params={
                "search": UNIQUE_TEST_MARKER,
                "page_number": 2,
                "page_size": 2,
            },
            headers=superuser_headers,
        )
        second_data = await assert_status_return_json(
            second_page, HTTPStatus.OK
        )
        assert len(second_data["items"]) == 1
        assert second_data["total"] == 3

        first_ids = {item["id"] for item in first_data["items"]}
        second_ids = {item["id"] for item in second_data["items"]}
        assert first_ids.isdisjoint(second_ids)

    async def test_list_users_without_auth(self, http_client: ClientSession):
        """Для пользователя без токена 401."""
        response = await http_client.get(ADMIN_USERS_URL + "/")
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_list_users_regular_user_without_permission(
        self,
        http_client: ClientSession,
        regular_user_headers: dict[str, str],
    ):
        """Запрос списка от обычного пользователя без права user:view_personal_data возвращает 403 с телом ошибки."""
        response = await http_client.get(
            ADMIN_USERS_URL + "/", headers=regular_user_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.FORBIDDEN)
        assert_error_detail(data)

    async def test_list_users_with_granted_permission(
        self,
        http_client: ClientSession,
        view_permission_granted_headers: dict[str, str],
    ):
        """Проверка, что у пользователя с правом user:view_personal_data через роль доступ есть."""
        response = await http_client.get(
            ADMIN_USERS_URL + "/", headers=view_permission_granted_headers
        )
        await assert_status_return_json(response, HTTPStatus.OK)


class TestGetUserProfile:
    """Тесты GET /admin/users/{user_id}/."""

    async def test_get_user_profile_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """Полный набор полей профиля, включая email_verified и timezone."""
        target = search_and_pagination_users[0]
        response = await http_client.get(
            f"{ADMIN_USERS_URL}/{target['id']}/", headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)

        assert data["id"] == str(target["id"])
        assert data["email"] == target["email"]
        assert data["full_name"] == target["full_name"]
        assert "email_verified" in data
        assert "timezone" in data

    async def test_get_user_profile_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Запрос профиля по несуществующему user_id возвращает 404 с телом ошибки."""
        response = await http_client.get(
            f"{ADMIN_USERS_URL}/{NOT_EXISTING_UUID}/",
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.NOT_FOUND)
        assert_error_detail(data)

    async def test_get_user_profile_without_auth(
        self,
        http_client: ClientSession,
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """Для пользователей без токена 401."""
        response = await http_client.get(
            f"{ADMIN_USERS_URL}/{search_and_pagination_users[0]['id']}/"
        )
        data = await assert_status_return_json(
            response, HTTPStatus.UNAUTHORIZED
        )
        assert_error_detail(data)

    async def test_get_user_profile_regular_user_without_permission(
        self,
        http_client: ClientSession,
        regular_user_headers: dict[str, str],
        search_and_pagination_users: list[dict[str, Any]],
    ):
        """Для обычного пользователя без права user:view_personal_data вернет 403."""
        response = await http_client.get(
            f"{ADMIN_USERS_URL}/{search_and_pagination_users[0]['id']}/",
            headers=regular_user_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.FORBIDDEN)
        assert_error_detail(data)
