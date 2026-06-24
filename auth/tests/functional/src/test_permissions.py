"""Функциональные тесты эндпоинтов прав доступа."""

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

PERMISSIONS_URL = f"{test_settings.api_prefix}/permissions"
ROLES_URL = f"{test_settings.api_prefix}/roles"


class TestCreatePermission:
    """Тесты создания права доступа POST /permissions/."""

    async def test_create_permission_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Суперпользователь успешно создаёт право (возвращается 201 с id, code, category)."""
        payload = {
            "code": f"test:{uuid.uuid4().hex[:8]}",
            "name": "Test permission",
            "category": "test",
        }
        response = await http_client.post(
            f"{PERMISSIONS_URL}/", json=payload, headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert "id" in data
        assert data["code"] == payload["code"]
        assert data["category"] == payload["category"]

    async def test_create_permission_duplicate(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_permission: dict[str, Any],
    ):
        """Создание права с уже существующим code возвращает 400."""
        response = await http_client.post(
            f"{PERMISSIONS_URL}/",
            json={"code": created_permission["code"], "name": "Duplicate"},
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.BAD_REQUEST)

    async def test_create_permission_invalid_code(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Создание права с кодом не в формате resource:action возвращает 422."""
        response = await http_client.post(
            f"{PERMISSIONS_URL}/",
            json={"code": "invalid-code-format", "name": "Test"},
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_create_permission_access_denied(
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
            f"{PERMISSIONS_URL}/",
            json={"code": f"test:{uuid.uuid4().hex[:8]}", "name": "Test"},
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestGetAllPermissions:
    """Тесты получения списка прав GET /permissions/."""

    async def test_get_all_permissions_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_permission: dict[str, Any],
    ):
        """Суперпользователь получает список прав, созданное право присутствует в ответе."""
        response = await http_client.get(
            f"{PERMISSIONS_URL}/", headers=superuser_headers
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert isinstance(data, list)
        assert any(p["id"] == created_permission["id"] for p in data)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_get_all_permissions_access_denied(
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
        response = await http_client.get(
            f"{PERMISSIONS_URL}/", headers=headers
        )
        await assert_status(response, expected_status)


class TestUpdatePermission:
    """Тесты обновления права PATCH /permissions/{permission_id}/."""

    async def test_update_permission_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_permission: dict[str, Any],
    ):
        """Суперпользователь обновляет name и description права."""
        payload = {
            "name": "Updated name",
            "description": "Updated description",
        }
        response = await http_client.patch(
            f"{PERMISSIONS_URL}/{created_permission['id']}/",
            json=payload,
            headers=superuser_headers,
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]

    async def test_update_permission_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Обновление несуществующего права возвращает 404."""
        response = await http_client.patch(
            f"{PERMISSIONS_URL}/{NOT_EXISTING_UUID}/",
            json={"name": "Updated"},
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_update_permission_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_permission: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.patch(
            f"{PERMISSIONS_URL}/{created_permission['id']}/",
            json={"name": "Updated"},
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestDeletePermission:
    """Тесты удаления права DELETE /permissions/{permission_id}/."""

    @pytest_asyncio.fixture(scope="function")
    async def permission_to_delete(
        self,
        session_http_client: ClientSession,
        superuser_headers: dict[str, str],
    ) -> dict[str, Any]:
        """Создаёт право без автоудаления."""
        payload = {
            "code": f"test:{uuid.uuid4().hex[:8]}",
            "name": "Permission to delete",
        }
        response = await session_http_client.post(
            f"{PERMISSIONS_URL}/", json=payload, headers=superuser_headers
        )
        return await response.json()

    async def test_delete_permission_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        permission_to_delete: dict[str, Any],
    ):
        """Суперпользователь удаляет право: возвращается 204."""
        response = await http_client.delete(
            f"{PERMISSIONS_URL}/{permission_to_delete['id']}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NO_CONTENT)

    async def test_delete_permission_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
    ):
        """Удаление несуществующего права возвращает 404."""
        response = await http_client.delete(
            f"{PERMISSIONS_URL}/{NOT_EXISTING_UUID}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_delete_permission_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_permission: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.delete(
            f"{PERMISSIONS_URL}/{created_permission['id']}/",
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestAssignPermissionToRole:
    """Тесты назначения права роли POST /roles/{role_id}/permissions/{permission_id}/."""

    async def test_assign_permission_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        created_permission: dict[str, Any],
    ):
        """Суперпользователь назначает право роли: возвращается 201."""
        role_id = created_role["id"]
        permission_id = created_permission["id"]
        response = await http_client.post(
            f"{ROLES_URL}/{role_id}/permissions/{permission_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.CREATED)
        await http_client.delete(
            f"{ROLES_URL}/{role_id}/permissions/{permission_id}/",
            headers=superuser_headers,
        )

    async def test_assign_permission_duplicate(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        created_permission: dict[str, Any],
    ):
        """Повторное назначение того же права той же роли возвращает 400."""
        role_id = created_role["id"]
        permission_id = created_permission["id"]
        await http_client.post(
            f"{ROLES_URL}/{role_id}/permissions/{permission_id}/",
            headers=superuser_headers,
        )
        response = await http_client.post(
            f"{ROLES_URL}/{role_id}/permissions/{permission_id}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.BAD_REQUEST)
        await http_client.delete(
            f"{ROLES_URL}/{role_id}/permissions/{permission_id}/",
            headers=superuser_headers,
        )

    async def test_assign_permission_role_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_permission: dict[str, Any],
    ):
        """Назначение права несуществующей роли возвращает 404."""
        response = await http_client.post(
            f"{ROLES_URL}/{NOT_EXISTING_UUID}/permissions/{created_permission['id']}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_assign_permission_not_found(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
    ):
        """Назначение несуществующего права роли возвращает 404."""
        response = await http_client.post(
            f"{ROLES_URL}/{created_role['id']}/permissions/{NOT_EXISTING_UUID}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_assign_permission_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        created_role: dict[str, Any],
        created_permission: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.post(
            f"{ROLES_URL}/{created_role['id']}/permissions/{created_permission['id']}/",
            headers=headers,
        )
        await assert_status(response, expected_status)


class TestRemovePermissionFromRole:
    """Тесты снятия права с роли DELETE /roles/{role_id}/permissions/{permission_id}/."""

    @pytest_asyncio.fixture(scope="function")
    async def assigned_permission(
        self,
        session_http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        created_permission: dict[str, Any],
    ) -> dict[str, Any]:
        """Назначает право роли через API для использования в тестах снятия."""
        await session_http_client.post(
            f"{ROLES_URL}/{created_role['id']}/permissions/{created_permission['id']}/",
            headers=superuser_headers,
        )
        return {
            "role_id": created_role["id"],
            "permission_id": created_permission["id"],
        }

    async def test_remove_permission_success(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        assigned_permission: dict[str, Any],
    ):
        """Суперпользователь снимает право с роли: возвращается 204."""
        response = await http_client.delete(
            f"{ROLES_URL}/{assigned_permission['role_id']}/permissions/{assigned_permission['permission_id']}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NO_CONTENT)

    async def test_remove_permission_not_assigned(
        self,
        http_client: ClientSession,
        superuser_headers: dict[str, str],
        created_role: dict[str, Any],
        created_permission: dict[str, Any],
    ):
        """Снятие права, которое не было назначено роли, возвращает 404."""
        response = await http_client.delete(
            f"{ROLES_URL}/{created_role['id']}/permissions/{created_permission['id']}/",
            headers=superuser_headers,
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    @pytest.mark.parametrize("auth,expected_status", ACCESS_DENIED_CASES)
    async def test_remove_permission_access_denied(
        self,
        http_client: ClientSession,
        no_auth_headers: dict[str, str],
        regular_user_headers: dict[str, str],
        assigned_permission: dict[str, Any],
        auth: str,
        expected_status: HTTPStatus,
    ):
        """Запрос без токена возвращает 401, от обычного пользователя 403."""
        headers = (
            regular_user_headers if auth == "regular_user" else no_auth_headers
        )
        response = await http_client.delete(
            f"{ROLES_URL}/{assigned_permission['role_id']}/permissions/{assigned_permission['permission_id']}/",
            headers=headers,
        )
        await assert_status(response, expected_status)
