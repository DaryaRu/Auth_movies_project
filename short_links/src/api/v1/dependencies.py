"""Зависимости для API."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.core.config import settings


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
