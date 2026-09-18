"""Зависимости для API."""

import logging
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import (
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Security,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.db.redis import Redis
from src.integrations.auth_client import AuthClient
from src.utils.jwt import decode_token

logger = logging.getLogger(__name__)

_SESSION_VALID_CACHE_KEY = "user_actions:session_valid:{sid}"

_bearer = HTTPBearer(auto_error=False)


def verify_internal_secret(
    x_internal_secret: str | None = Header(default=None),
) -> None:
    """Требует X-Internal-Secret для вызовов от другого сервиса."""
    if (
        not settings.INTERNAL_SERVICE_SECRET
        or x_internal_secret is None
        or not secrets.compare_digest(
            x_internal_secret, settings.INTERNAL_SERVICE_SECRET
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal secret",
        )


InternalServiceDep = Annotated[None, Depends(verify_internal_secret)]


class PaginationParams:
    """Параметры пагинации для endpoints."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Номер страницы"),
        page_size: int = Query(
            default=settings.PAGINATION_DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.PAGINATION_MAX_PAGE_SIZE,
            description="Количество элементов на странице",
        ),
    ):
        self.page = page
        self.page_size = page_size


def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(
        default=settings.PAGINATION_DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.PAGINATION_MAX_PAGE_SIZE,
        description="Количество элементов на странице",
    ),
) -> PaginationParams:
    """Создать параметры пагинации."""
    return PaginationParams(page=page, page_size=page_size)


async def _verify_session(sid: str) -> bool:
    """Проверить действительность сессии через auth-service.

    Сессия считается действительной, если auth-service подтверждает её
    активность и существование активного пользователя. Подтверждённые
    сессии кэшируются в Redis на SESSION_VERIFY_CACHE_TTL секунд, чтобы
    не нагружать auth-service каждым запросом.

    Fail-closed: при недоступности auth-service или непредвиденном ответе
    сессия считается недействительной.
    """
    use_cache = settings.SESSION_VERIFY_CACHE_TTL > 0
    redis_client = Redis.get_client() if use_cache else None
    cache_key = _SESSION_VALID_CACHE_KEY.format(sid=sid)

    if redis_client is not None:
        try:
            if await redis_client.get(cache_key):
                return True
        except Exception as e:
            logger.warning(
                "Redis unavailable, verifying session directly: %s", e
            )

    try:
        valid = await AuthClient.verify_session(sid)
    except Exception as e:
        logger.warning("Session verify failed for sid %s: %s", sid, e)
        return False

    if valid and redis_client is not None:
        try:
            await redis_client.set(
                cache_key, "1", ex=settings.SESSION_VERIFY_CACHE_TTL
            )
        except Exception as e:
            logger.warning("Failed to cache session validity: %s", e)
    return valid


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(_bearer)
    ] = None,
) -> UUID:
    """Получить текущего пользователя из JWT-токена.

    Проверяет:
    - подпись токена и срок его действия;
    - тип токена: принимается только access (refresh-токен как Bearer
      отклоняется);
    - действительность сессии и аккаунта через auth-service по claim `sid`
      (согласованный механизм отзыва: после logout, смены телефона или
      удаления аккаунта выданный токен перестаёт работать).
    """
    exception_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise exception_401
    payload = await decode_token(credentials.credentials)
    if payload is None:
        raise exception_401
    if payload.get("type") != "access":
        raise exception_401
    sid = payload.get("sid")
    if not isinstance(sid, str) or not sid:
        raise exception_401
    if not await _verify_session(sid):
        raise exception_401
    user_id = payload.get("sub")
    if not user_id:
        raise exception_401
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise exception_401 from None

    request.state.user_id = user_uuid
    return user_uuid


PaginationDepend = Annotated[PaginationParams, Depends(get_pagination_params)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user)]

__all__ = [
    "PaginationDepend",
    "PaginationParams",
    "CurrentUserDep",
]
