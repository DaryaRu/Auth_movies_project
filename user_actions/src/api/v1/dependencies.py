"""Зависимости для API."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, Security, status
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


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> UUID:
    """Получить текущего пользователя из JWT-токена."""
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
    user_id = payload.get("sub")
    if not user_id:
        raise exception_401
    user_uuid = UUID(user_id)
    request.state.user_id = user_uuid
    return user_uuid


PaginationDepend = Annotated[PaginationParams, Depends(get_pagination_params)]
CurrentUserDep = Annotated[UUID, Depends(get_current_user)]

__all__ = [
    "PaginationDepend",
    "PaginationParams",
    "CurrentUserDep",
]
