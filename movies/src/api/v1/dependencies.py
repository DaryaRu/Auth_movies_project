"""Dependencies for API."""

from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Query, status

from core import config
from utils.jwt import decode_token


class PaginationParams:
    """Pagination parameters for endpoints."""

    def __init__(
        self,
        page_number: int = Query(
            default=1, ge=1, description="Номер запрашиваемой страницы."
        ),
        page_size: int = Query(
            default=config.PAGINATION_DEFAULT_PAGE_SIZE,
            ge=1,
            le=config.PAGINATION_MAX_PAGE_SIZE,
            description="Количество элементов на одной странице.",
        ),
    ):
        self.page_number = page_number
        self.page_size = page_size


PaginationDepend = Annotated[PaginationParams, Depends(PaginationParams)]


async def get_token_payload(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any] | None:
    """Декодирует Bearer-токен из заголовка Authorization. Возвращает None если токен отсутствует или невалиден."""
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return await decode_token(token)


async def require_token_payload(
    payload: Annotated[dict[str, Any] | None, Depends(get_token_payload)],
) -> dict[str, Any]:
    """Требует валидный JWT-токен. Возвращает 401 если токен отсутствует или невалиден."""
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


OptionalTokenPayloadDep = Annotated[dict[str, Any] | None, Depends(get_token_payload)]
RequiredTokenPayloadDep = Annotated[dict[str, Any], Depends(require_token_payload)]
