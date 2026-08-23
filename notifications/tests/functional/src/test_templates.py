"""CRUD и превью шаблонов уведомлений (`/api/v1/notifications/templates/`)."""

from http import HTTPStatus
from uuid import uuid4

import pytest
from aiohttp import ClientSession
from settings import test_settings
from utils.check_methods import assert_status, assert_status_return_json

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = f"{test_settings.api_v1_prefix}/notifications/templates/"


def _unique_code() -> str:
    return f"functest_{uuid4().hex[:12]}"


def _template_payload(**overrides) -> dict:
    payload = {
        "code": _unique_code(),
        "name": "Functional test template",
        "channel": "email",
        "subject": "Тема {{ movie_title }}",
        "body": "Новый фильм: {{ movie_title }}!",
        "allowed_variables": ["movie_title"],
        "is_active": True,
    }
    payload.update(overrides)
    return payload


class TestTemplateCreate:
    """POST /notifications/templates/."""

    async def test_create_success(self, http_client: ClientSession):
        """Позитивный тест создания шаблона. Возвращается 201 с полным
        объектом шаблона."""
        response = await http_client.post(BASE_URL, json=_template_payload())
        data = await assert_status_return_json(response, HTTPStatus.CREATED)
        assert data["template_id"]
        assert data["code"].startswith("functest_")
        assert data["channel"] == "email"
        assert data["allowed_variables"] == ["movie_title"]
        assert data["is_active"] is True

    async def test_duplicate_code_returns_conflict(
        self, http_client: ClientSession
    ):
        """Повторное создание шаблона с тем же code. 409."""
        payload = _template_payload()
        first = await http_client.post(BASE_URL, json=payload)
        await assert_status(first, HTTPStatus.CREATED)

        second = await http_client.post(BASE_URL, json=payload)
        await assert_status(second, HTTPStatus.CONFLICT)

    async def test_invalid_jinja_syntax_rejected(
        self, http_client: ClientSession
    ):
        """Синтаксическая ошибка Jinja2 в body. 422."""
        payload = _template_payload(body="Новый фильм: {{ movie_title !")
        response = await http_client.post(BASE_URL, json=payload)
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_unknown_variable_rejected(self, http_client: ClientSession):
        """Переменная в body, не входящая в allowed_variables. 422."""
        payload = _template_payload(
            body="Новый фильм: {{ unknown_var }}!",
            allowed_variables=["movie_title"],
        )
        response = await http_client.post(BASE_URL, json=payload)
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_nested_variable_access_rejected(
        self, http_client: ClientSession
    ):
        """{{ var.attr }} запрещен."""
        payload = _template_payload(
            body="{{ movie.year }}", allowed_variables=["movie"]
        )
        response = await http_client.post(BASE_URL, json=payload)
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestTemplateGet:
    """GET /notifications/templates/, /{id}/, /by-code/{code}/."""

    async def test_get_by_id(self, http_client: ClientSession):
        """Созданный шаблон находится по своему template_id."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.get(
            f"{BASE_URL}{created['template_id']}/"
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["template_id"] == created["template_id"]
        assert data["code"] == created["code"]

    async def test_get_by_id_not_found(self, http_client: ClientSession):
        """Несуществующий template_id. 404."""
        response = await http_client.get(f"{BASE_URL}{uuid4()}/")
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_get_by_code(self, http_client: ClientSession):
        """Созданный шаблон находится по своему code."""
        payload = _template_payload()
        await http_client.post(BASE_URL, json=payload)

        response = await http_client.get(
            f"{BASE_URL}by-code/{payload['code']}/"
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["code"] == payload["code"]

    async def test_get_by_code_not_found(self, http_client: ClientSession):
        """Несуществующий code. 404."""
        response = await http_client.get(
            f"{BASE_URL}by-code/{_unique_code()}/"
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_list_includes_created(self, http_client: ClientSession):
        """Список шаблонов включает только что созданный."""
        payload = _template_payload()
        await http_client.post(BASE_URL, json=payload)

        response = await http_client.get(BASE_URL)
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert isinstance(data, list)
        assert any(t["code"] == payload["code"] for t in data)


class TestTemplateUpdate:
    """PATCH /notifications/templates/{id}/."""

    async def test_partial_update(self, http_client: ClientSession):
        """Частичное обновление меняет только переданные поля, остальные нет."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.patch(
            f"{BASE_URL}{created['template_id']}/",
            json={"is_active": False},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["is_active"] is False
        assert data["name"] == created["name"]
        assert data["body"] == created["body"]

    async def test_update_not_found(self, http_client: ClientSession):
        """Несуществующий template_id. 404."""
        response = await http_client.patch(
            f"{BASE_URL}{uuid4()}/", json={"is_active": False}
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)

    async def test_update_with_invalid_content_rejected(
        self, http_client: ClientSession
    ):
        """Обновление body синтаксически некорректным Jinja2. 422."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.patch(
            f"{BASE_URL}{created['template_id']}/",
            json={"body": "Новый фильм: {{ movie_title !"},
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestTemplatePreview:
    """POST /notifications/templates/{id}/preview/."""

    async def test_preview_renders_with_payload(
        self, http_client: ClientSession
    ):
        """Позитивный тест: payload подставляется в subject и body."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.post(
            f"{BASE_URL}{created['template_id']}/preview/",
            json={"payload": {"movie_title": "Матрица"}},
        )
        data = await assert_status_return_json(response, HTTPStatus.OK)
        assert data["subject"] == "Тема Матрица"
        assert data["body"] == "Новый фильм: Матрица!"

    async def test_preview_missing_variable_rejected(
        self, http_client: ClientSession
    ):
        """В payload не хватает переменной, которую ждет шаблон. 422."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.post(
            f"{BASE_URL}{created['template_id']}/preview/",
            json={"payload": {}},
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_preview_unknown_payload_key_rejected(
        self, http_client: ClientSession
    ):
        """Payload содержит ключ, не входящий в allowed_variables шаблона. 422."""
        create_response = await http_client.post(
            BASE_URL, json=_template_payload()
        )
        created = await create_response.json()

        response = await http_client.post(
            f"{BASE_URL}{created['template_id']}/preview/",
            json={"payload": {"movie_title": "Матрица", "unexpected": "x"}},
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_preview_unknown_payload_key_rejected_with_empty_allowed_variables(
        self, http_client: ClientSession
    ):
        """allowed_variables=[] не отключает валидацию payload."""
        create_response = await http_client.post(
            BASE_URL,
            json=_template_payload(
                subject="Тема без переменных",
                body="Текст без переменных.",
                allowed_variables=[],
            ),
        )
        await assert_status(create_response, HTTPStatus.CREATED)
        created = await create_response.json()

        response = await http_client.post(
            f"{BASE_URL}{created['template_id']}/preview/",
            json={"payload": {"unexpected": "x"}},
        )
        await assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    async def test_preview_not_found(self, http_client: ClientSession):
        """Несуществующий template_id. 404."""
        response = await http_client.post(
            f"{BASE_URL}{uuid4()}/preview/",
            json={"payload": {}},
        )
        await assert_status(response, HTTPStatus.NOT_FOUND)
