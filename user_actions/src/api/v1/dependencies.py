"""Зависимости для API."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.utils.jwt import decode_token

_bearer = HTTPBearer(auto_error=False)


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


PaginationDepend = Annotated[PaginationParams, Depends(get_pagination_params)]

__all__ = [
    "PaginationDepend", 
    "PaginationParams", 
    "OptionalTokenPayloadDep", 
    "RequiredTokenPayloadDep"
]

async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> dict[str, Any] | None:
    """Декодирует Bearer-токен из Swagger/Заголовка. Возвращает None если токен отсутствует."""
    if credentials is None:
        return None
    
    return await decode_token(credentials.credentials)


async def require_token_payload(
    payload: Annotated[dict[str, Any] | None, Depends(get_token_payload)],
) -> UUID:
    """Требует валидный JWT-токен. Возвращает 401 если токен отсутствует или невалиден."""
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return UUID(user_id)


OptionalTokenPayloadDep = Annotated[dict[str, Any] | None, Depends(get_token_payload)]
RequiredTokenPayloadDep = Annotated[UUID, Depends(require_token_payload)]
