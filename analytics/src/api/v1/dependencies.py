import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.db import redis
from src.integrations.auth_client import AuthClient
from src.utils.jwt import decode_token

logger = logging.getLogger(__name__)

_SESSION_VALID_CACHE_KEY = "analytics:session_valid:{sid}"

_bearer = HTTPBearer()


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
    cache_key = _SESSION_VALID_CACHE_KEY.format(sid=sid)

    if use_cache and redis.redis is not None:
        try:
            if await redis.redis.get(cache_key):
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

    if valid and use_cache and redis.redis is not None:
        try:
            await redis.redis.set(
                cache_key, "1", ex=settings.SESSION_VERIFY_CACHE_TTL
            )
        except Exception as e:
            logger.warning("Failed to cache session validity: %s", e)
    return valid


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> UUID:
    """Получить текущего пользователя из JWT-токена.

    Проверяет подпись и срок действия токена, тип токена (принимается
    только access — refresh-токен как Bearer отклоняется) и действительность
    сессии/аккаунта через auth-service по claim `sid` (согласованный
    механизм отзыва: после logout, смены телефона или удаления аккаунта
    выданный токен перестаёт работать).
    """
    exception_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
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


CurrentUserDep = Annotated[UUID, Depends(get_current_user)]
