"""Rate limiter для приложения."""

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from src.core.config import settings


def get_user_id_key(request: Request) -> str:
    """Получение ключа для идентификации пользователя.

    Args:
        request: Объект запроса.

    Returns:
        str: ID пользователя или 'anonymous', если пользователь не аутентифицирован.
    """
    user_id = getattr(request.state, "user_id", None)
    return str(user_id) if user_id is not None else "anonymous"


limiter = Limiter(
    key_func=get_user_id_key,
    storage_uri=settings.REDIS_URL,
    default_limits=[settings.EVENTS_RATE_LIMIT],
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Обработчик превышения лимита запросов.

    Args:
        request: Объект запроса.
        exc: Исключение превышения лимита.

    Returns:
        Response с кодом 429 и сообщением о слишком большом количестве запросов.
    """
    return Response(
        content='{"detail":"Too Many Requests"}',
        status_code=429,
        media_type="application/json",
    )
