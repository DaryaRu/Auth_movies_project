"""Зависимости для API."""

import secrets
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.utils.jwt import decode_token

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


async def get_current_staff_payload(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
) -> dict[str, Any]:
    """Требует JWT суперпользователя (CRUD шаблонов, рассылки в админке)."""
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
    if not payload.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return payload


StaffUserDep = Annotated[dict[str, Any], Depends(get_current_staff_payload)]
