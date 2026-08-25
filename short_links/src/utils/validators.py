"""Утилиты валидации URL для защиты от Open Redirect."""

from urllib.parse import urlparse

from src.core.config import settings


class InvalidRedirectUrlError(ValueError):
    """Бросается при валидации недопустимого redirect_url."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def validate_redirect_url(url: str) -> str:
    """Валидирует redirect_url: абсолютный, схема http/https, хост в allowlist.

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

    allowed_hosts = settings.ALLOWED_REDIRECT_HOSTS_SET
    if host.lower() not in allowed_hosts:
        raise InvalidRedirectUrlError(
            f"Хост '{host}' не входит в разрешённый список. "
            f"Разрешены: {', '.join(sorted(allowed_hosts))}"
        )

    return url