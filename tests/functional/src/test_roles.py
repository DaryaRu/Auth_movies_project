"""Функциональные тесты эндпоинтов ролей."""

import uuid
from http import HTTPStatus
from typing import Any

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from functional.settings import test_settings
from functional.utils.check_methods import (
    assert_status,
    assert_status_return_json,
)
from functional.utils.constants import ACCESS_DENIED_CASES, NOT_EXISTING_UUID

pytestmark = pytest.mark.asyncio(loop_scope="session")

ROLES_URL = f"{test_settings.api_prefix}/roles"


class TestCreateRole:
    """Тесты создания роли POST /roles/."""

    async def test_create_role_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Суперпользователь успешно создаёт роль (возвращается 201 с id, is_active=True, is_system=False)."""
        payload = {
            "name": f"role_{uuid.uuid4().hex[:8]}",
            "description": "Test",
        }
        response = await http_client.post(
            f"{ROLES_URL}/", json=payload, headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["is_active"] is True
        assert data["is_system"] is False

    async def test_create_role_invalid_data(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Запрос на создание роли без обязательного поля name возвращает 422."""
        response = await http_client.post(
            f"{ROLES_URL}/", json={}, headers=superuser_headers
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_create_role_duplicate(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Создание роли с уже существующим именем возвращает 400."""
        response = await http_client.post(
            f"{ROLES_URL}/",
            json={"name": created_role["name"]},
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.BAD_REQUEST)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_create_role_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.post(
            f"{ROLES_URL}/",
            json={"name": f"role_{uuid.uuid4().hex[:8]}"},
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestGetAllRoles:
    """Тесты получения списка ролей GET /roles/."""

    async def test_get_all_roles_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Суперпользователь получает список ролей, созданная роль есть в ответе."""
        response = await http_client.get(
            f"{ROLES_URL}/", headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert isinstance(data, list)
        assert any(role["id"] == created_role["id"] for role in data)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_get_all_roles_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя — 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.get(f"{ROLES_URL}/", headers=headers)
        await assert_status(response, expected_status)


class TestGetRoleDetail:
    """Тесты получения информации о роли GET /roles/{role_id}/."""

    async def test_get_role_detail_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Детали роли содержат id, name и список прав."""
        response = await http_client.get(
            f"{ROLES_URL}/{created_role['id']}/", headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["id"] == created_role["id"]
        assert data["name"] == created_role["name"]
        assert "permissions" in data
        assert isinstance(data["permissions"], list)

    async def test_get_role_detail_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Запрос несуществующей роли возвращает 404."""
        response = await http_client.get(
            f"{ROLES_URL}/{NOT_EXISTING_UUID}/", headers=superuser_headers
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_get_role_detail_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_role: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.get(
            f"{ROLES_URL}/{created_role['id']}/", headers=headers
        )
        await assert_status(response, expected_status)


class TestUpdateRole:
    """Тесты обновления роли PATCH /roles/{role_id}/."""

    async def test_update_role_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Суперпользователь обновляет описание и is_active роли."""
        payload = {"description": "Updated description", "is_active": False}
        response = await http_client.patch(
            f"{ROLES_URL}/{created_role['id']}/",
            json=payload,
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["description"] == payload["description"]
        assert data["is_active"] is False

    async def test_update_role_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Обновление несуществующей роли возвращает 404."""
        response = await http_client.patch(
            f"{ROLES_URL}/{NOT_EXISTING_UUID}/",
            json={"description": "Updated description"},
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_update_role_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_role: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.patch(
            f"{ROLES_URL}/{created_role['id']}/",
            json={"description": "x"},
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestDeleteRole:
    """Тесты удаления роли DELETE /roles/{role_id}/."""

    @pytest_asyncio.fixture(scope="function")
    async def role_to_delete(
        self,
        session_http_client: ClientSession,
        superuser_headers: dict[str, str],
    ) -> dict[str, Any]:
        """Роль создается через API без автоудаления."""
        payload = {"name": f"to_delete_{uuid.uuid4().hex[:8]}"}
        response = await session_http_client.post(
            f"{ROLES_URL}/", json=payload, headers=superuser_headers
        )
        return await response.json()

    async def test_delete_role_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        role_to_delete: dict[str, Any],
    ):
        """Суперпользователь удаляет роль: возвращается 204 без тела ответа."""
        response = await http_client.delete(
            f"{ROLES_URL}/{role_to_delete['id']}/", headers=superuser_headers
        )
        await assert_status(response, HTTPStatus.NO_CONTENT)

    async def test_delete_role_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Удаление несуществующей роли возвращает 404."""
        response = await http_client.delete(
            f"{ROLES_URL}/{NOT_EXISTING_UUID}/", headers=superuser_headers
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_delete_system_role_conflict(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        system_role: dict[str, Any],
    ):
        """Попытка удалить системную роль (is_system=True) возвращает 409."""
        response = await http_client.delete(
            f"{ROLES_URL}/{system_role['id']}/", headers=superuser_headers
        )
        await assert_status(response, HTTPStatus.CONFLICT)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_delete_role_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_role: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.delete(
            f"{ROLES_URL}/{created_role['id']}/", headers=headers
        )
        await assert_status(response, expected_status)


class TestAssignRoleToUser:
    """Тесты назначения роли пользователю POST /roles/{role_id}/users/{user_id}/."""

    async def test_assign_role_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        regular_user_for_roles_data: dict[str, Any],
    ):
        """Суперпользователь назначает роль пользователю: возвращается 201."""
        user_id = regular_user_for_roles_data["id"]
        role_id = created_role["id"]
        response = await http_client.post(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.CREATED)
        await http_client.delete(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )

    async def test_assign_role_duplicate(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        regular_user_for_roles_data: dict[str, Any],
    ):
        """Повторное назначение той же роли тому же пользователю возвращает 400."""
        user_id = regular_user_for_roles_data["id"]
        role_id = created_role["id"]
        await http_client.post(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )
        response = await http_client.post(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.BAD_REQUEST)
        await http_client.delete(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )

    async def test_assign_role_user_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Назначение роли несуществующему пользователю возвращает 404."""
        response = await http_client.post(
            f"{ROLES_URL}/{created_role['id']}/users/{NOT_EXISTING_UUID}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_assign_role_role_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        regular_user_for_roles_data: dict[str, Any],
    ):
        """Назначение несуществующей роли пользователю возвращает 404."""
        user_id = regular_user_for_roles_data["id"]
        response = await http_client.post(
            f"{ROLES_URL}/{NOT_EXISTING_UUID}/users/{user_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)


class TestRemoveRoleFromUser:
    """Тесты снятия роли с пользователя DELETE /roles/{role_id}/users/{user_id}/."""

    @pytest_asyncio.fixture(scope="function")
    async def assigned_role(
        self,
        session_http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        regular_user_for_roles_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Назначает роль пользователю через API для использования в тестах снятия."""
        user_id = regular_user_for_roles_data["id"]
        role_id = created_role["id"]
        await session_http_client.post(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )
        return {"role_id": role_id, "user_id": str(user_id)}

    async def test_remove_role_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        assigned_role: dict[str, Any],
    ):
        """Суперпользователь снимает роль с пользователя: возвращается 204."""
        response = await http_client.delete(
            f"{ROLES_URL}/{assigned_role['role_id']}/users/{assigned_role['user_id']}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NO_CONTENT)

    async def test_remove_role_not_assigned(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        regular_user_for_roles_data: dict[str, Any],
    ):
        """Снятие роли, которая не была назначена пользователю, возвращает 404."""
        user_id = regular_user_for_roles_data["id"]
        role_id = created_role["id"]
        response = await http_client.delete(
            f"{ROLES_URL}/{role_id}/users/{user_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)
