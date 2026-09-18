"""Поддержание валидного access-токена для API-вызовов из админки.

Access-токен, сохранённый в сессию при логине, живёт на стороне
auth-service всего ACCESS_TOKEN_EXPIRE_MINUTES (5 минут). После
истечения он обновляется через endpoint /refresh/ с использованием
refresh-токена, который перехватывается из cookie ответа при логине.

Важно: auth-service делает ротацию токенов — старый refresh-токен
инвалидируется, а новый возвращается в cookie ответа. Поэтому после
успешного рефреша в сессию сохраняются оба новых значения.
"""

import http
import logging
import time
import uuid

import requests
from django.conf import settings
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Запас времени до истечения (в секундах). Если до exp осталось меньше
# этого, токен считается истёкшим. Управляет разницей часов между
# Django и auth-service.
EXPIRY_MARGIN_SECONDS = 60

AUTH_API_TIMEOUT = 5


def get_valid_access_token(session) -> str | None:
    """Вернуть валидный access-токен из сессии, при необходимости обнови.

    Если токен истёк, он обновляется через auth-service по
    refresh-токену из сессии. Если обновление не удалось, возвращается
    старый токен (best effort: при временной недоступности auth-service
    он может жить ещё).
    """
    access_token = session.get("access_token")
    if not access_token:
        return None

    if _is_token_valid(access_token):
        return access_token

    new_access_token = _refresh_access_token(session)
    return new_access_token or access_token


def _is_token_valid(access_token: str) -> bool:
    """Проверить срок действия токена без верификации подписи."""
    try:
        payload = jwt.decode(
            access_token,
            "",
            options={"verify_signature": False, "verify_exp": False},
        )
    except JWTError:
        return False

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return False
    return time.time() < exp - EXPIRY_MARGIN_SECONDS


def _refresh_access_token(session) -> str | None:
    """Обменять refresh-токен сессии на новую пару токенов."""
    refresh_token = session.get("refresh_token")
    if not refresh_token:
        logger.error(
            "Access token expired and no refresh token in session"
        )
        return None

    try:
        response = requests.post(
            f"{settings.AUTH_API_BASE_URL}/refresh/",
            cookies={"refresh_token": refresh_token},
            timeout=AUTH_API_TIMEOUT,
            headers={"X-Request-Id": str(uuid.uuid4())},
        )
    except requests.RequestException as exc:
        logger.error("Token refresh request failed: %s", exc)
        return None

    if response.status_code != http.HTTPStatus.OK:
        logger.error(
            "Token refresh status code - %s: %s",
            response.status_code,
            response.text,
        )
        return None

    try:
        new_access_token = response.json()["access_token"]
    except (ValueError, KeyError) as exc:
        logger.error("Unexpected token refresh response: %s", exc)
        return None

    # Ротация: auth-service инвалидирует старый refresh-токен и
    # возвращает новый в cookie ответа.
    new_refresh_token = response.cookies.get("refresh_token")
    session["access_token"] = new_access_token
    if new_refresh_token:
        session["refresh_token"] = new_refresh_token
    session.modified = True
    return new_access_token
