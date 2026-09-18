"""Функциональные тесты отзыва доступа в user_actions.

Проверяют, что get_current_user:
- требует type=access (refresh-токен как Bearer отклоняется);
- требует валидный claim sid;
- проверяет действительность сессии и аккаунта через auth-service
  (после logout и после удаления аккаунта выданный access-токен перестаёт
  работать, а данные удалённого пользователя очищаются).
"""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from uuid import uuid4

import asyncpg
import jwt
import pytest
from aiohttp import ClientSession

from tests.functional.utils.auth_api import (
    AuthSession,
    delete_account,
    logout,
)
from tests.functional.utils.check_methods import assert_status
from tests.settings import test_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")

MY_BOOKMARKS_URL = "/api/v1/user-actions/bookmarks/my"
CREATE_BOOKMARK_URL = "/api/v1/user-actions/bookmarks/"


def _forge_token(payload: dict) -> str:
    """Подписывает произвольный payload приватным ключом тестов."""
    with open(test_settings.private_key_path, "r", encoding="utf-8") as f:
        private_key = f.read()
    payload = {
        "sub": str(uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        **payload,
    }
    return jwt.encode(
        payload, private_key, algorithm=test_settings.jwt_algorithm
    )


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _get_my_bookmarks(http_client: ClientSession, token: str) -> int:
    response = await http_client.get(
        MY_BOOKMARKS_URL, headers=_auth_header(token)
    )
    await response.read()
    return response.status


class TestTokenTypeEnforced:
    """Только access-токены принимаются как Bearer."""

    async def test_refresh_token_rejected_as_bearer(
        self, http_client: ClientSession
    ):
        """Refresh-токен (type=refresh) как Bearer отклоняется с 401."""
        token = _forge_token({"type": "refresh", "sid": str(uuid4())})
        status = await _get_my_bookmarks(http_client, token)
        assert status == HTTPStatus.UNAUTHORIZED

    async def test_token_without_type_rejected(
        self, http_client: ClientSession
    ):
        """Токен без claim type отклоняется с 401."""
        token = _forge_token({"sid": str(uuid4())})
        status = await _get_my_bookmarks(http_client, token)
        assert status == HTTPStatus.UNAUTHORIZED

    async def test_token_without_sid_rejected(
        self, http_client: ClientSession
    ):
        """Access-токен без claim sid отклоняется с 401 (нет сессии для проверки)."""
        token = _forge_token({"type": "access"})
        status = await _get_my_bookmarks(http_client, token)
        assert status == HTTPStatus.UNAUTHORIZED

    async def test_forged_sid_without_session_rejected(
        self, http_client: ClientSession
    ):
        """Access-токен с несуществующим в auth-service sid отклоняется с 401."""
        token = _forge_token({"type": "access", "sid": str(uuid4())})
        status = await _get_my_bookmarks(http_client, token)
        assert status == HTTPStatus.UNAUTHORIZED

    async def test_valid_access_token_accepted(
        self, http_client: ClientSession, test_auth_session: AuthSession
    ):
        """Реальный access-токен с активной сессией принимается (200)."""
        status = await _get_my_bookmarks(
            http_client, test_auth_session.access_token
        )
        assert status == HTTPStatus.OK


class TestSessionRevocation:
    """Отзыв сессии мгновенно лишает токен доступа."""

    async def test_token_invalid_after_logout(
        self, http_client: ClientSession, test_auth_session: AuthSession
    ):
        """После logout access-токен перестаёт работать (401)."""
        status_before = await _get_my_bookmarks(
            http_client, test_auth_session.access_token
        )
        assert status_before == HTTPStatus.OK

        await logout(test_auth_session.refresh_token)

        status_after = await _get_my_bookmarks(
            http_client, test_auth_session.access_token
        )
        assert status_after == HTTPStatus.UNAUTHORIZED


class TestAccountDeletionRevocation:
    """После удаления аккаунта токен мёртв, данные очищены."""

    async def test_token_invalid_and_data_cleaned_after_delete(
        self,
        http_client: ClientSession,
        pg_client: asyncpg.Connection,
        test_auth_session: AuthSession,
    ):
        """После удаления аккаунта access-токен отклоняется (401), а данные
        пользователя в user_actions очищены обратным вызовом auth-service."""
        movie_id = uuid4()

        create_response = await http_client.post(
            CREATE_BOOKMARK_URL,
            json={"movie_id": str(movie_id)},
            headers=_auth_header(test_auth_session.access_token),
        )
        await assert_status(create_response, HTTPStatus.CREATED)

        await delete_account(test_auth_session.access_token)

        status_after = await _get_my_bookmarks(
            http_client, test_auth_session.access_token
        )
        assert status_after == HTTPStatus.UNAUTHORIZED

        bookmark_count = await pg_client.fetchval(
            "SELECT COUNT(*) FROM bookmarks WHERE user_id = $1",
            test_auth_session.user_id,
        )
        assert bookmark_count == 0
