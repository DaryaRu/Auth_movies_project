"""Работа с короткими ссылками через short-links-service."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import UUID

import httpx

from src.core.config import settings
from src.databases import http_client

logger = logging.getLogger(__name__)

SHORT_LINKS_SETTINGS_REDIRECT_URL = "/settings/redirect-url/"
SHORT_LINKS_SHORT_LINKS = "/short-links/"


class InvalidRedirectUrlError(ValueError):
    """Недопустимый redirect_url."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_redirect_url(url: str) -> str:
    """Валидирует redirect_url

    Args:
        url: URL для валидации.

    Returns:
        Валидированный URL (без изменений).

    Raises:
        InvalidRedirectUrlError: Если URL не соответствует требованиям.
    """
    if not url:
        raise InvalidRedirectUrlError("redirect_url не может быть пустым")

    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        raise InvalidRedirectUrlError(
            "redirect_url должен быть абсолютным URL (https://...)"
        )

    if parsed.scheme not in ("http", "https"):
        raise InvalidRedirectUrlError(
            f"Недопустимая схема '{parsed.scheme}'. Разрешены: http, https"
        )

    host = parsed.hostname
    if not host:
        raise InvalidRedirectUrlError("redirect_url должен содержать хост")

    allowed_hosts = set()
    if settings.ALLOWED_REDIRECT_HOSTS:
        allowed_hosts = {h.strip() for h in settings.ALLOWED_REDIRECT_HOSTS.split(",") if h.strip()}
    
    if not allowed_hosts:
        allowed_hosts = {settings.DEFAULT_REDIRECT_HOST}
    
    if settings.SHORT_LINKS_API_URL:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{settings.SHORT_LINKS_API_URL}{SHORT_LINKS_SETTINGS_REDIRECT_URL}",
                    headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                    timeout=5,
                )
                if response.status_code == 200:
                    allowed_hosts.add(host)
        except httpx.HTTPError:
            pass

    if host.lower() not in allowed_hosts:
        raise InvalidRedirectUrlError(
            f"Хост '{host}' не входит в разрешённый список. "
            f"Разрешены: {', '.join(sorted(allowed_hosts))}"
        )

    return url


async def _get_redirect_url() -> str:
    """Получить redirect_url из настроек short-links-service.

    Значение настраивается в панели админа.
    По умолчанию — главная страница онлайн-кинотеатра.
    """
    try:
        assert http_client.client is not None
        response = await http_client.client.get(
                f"{settings.SHORT_LINKS_API_URL}{SHORT_LINKS_SETTINGS_REDIRECT_URL}",
                headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
                timeout=5,
            )
        response.raise_for_status()
        redirect_url = response.json()["redirect_url"]
        
        validate_redirect_url(redirect_url)
        return redirect_url
    except httpx.HTTPError:
        logger.warning(
            "Не удалось получить redirect_url из short-links-service, "
            "использую значение по умолчанию"
        )
        return "http://localhost/"


async def create_short_link(
    user_id: UUID,
) -> str:
    """Создать короткую ссылку для подтверждения email.

    Args:
        user_id: Идентификатор пользователя.

    Returns:
        str: Короткая ссылка.

    Raises:
        httpx.HTTPError: Если запрос к short-links-service не удался.
        InvalidRedirectUrlError: Если redirect_url не прошёл валидацию.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    redirect_url = await _get_redirect_url()

    try:
        validate_redirect_url(redirect_url)
    except InvalidRedirectUrlError as e:
        logger.error(
            "Недопустимый redirect_url для пользователя %s: %s", user_id, e.message
        )
        raise

    payload = {
        "user_id": str(user_id),
        "expires_at": expires_at.isoformat(),
        "redirect_url": redirect_url,
    }

    try:
        assert http_client.client is not None
        response = await http_client.client.post(
            f"{settings.SHORT_LINKS_API_URL}{SHORT_LINKS_SHORT_LINKS}",
            json=payload,
            headers={"X-Internal-Secret": settings.INTERNAL_SERVICE_SECRET},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data["short_link"]
    except httpx.HTTPError as e:
        logger.error("Failed to create short link for user %s: %s", user_id, e)
        raise
    