"""API endpoints для закладок."""

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.v1.dependencies import CurrentUserDep
from src.core.config import settings
from src.repositories.bookmarks import BookmarkRepository
from src.schemas.bookmarks import (
    BookmarkCreate,
    BookmarkResponse,
    BookmarksListResponse,
)
from src.services.bookmarks import BookmarkService

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])
limiter = Limiter(key_func=get_remote_address)


def get_bookmark_service() -> BookmarkService:
    """Получить сервис закладок."""
    repository = BookmarkRepository()
    return BookmarkService(repository)


BookmarkServiceDep = Depends(get_bookmark_service)


@router.post(
    "/",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить закладку",
    description="Добавить фильм в закладки текущего пользователя",
)
@limiter.limit(settings.BOOKMARKS_RATE_LIMIT)
async def create_bookmark(
    request: Request,
    bookmark_data: BookmarkCreate,
    user_id: CurrentUserDep,
    bookmark_service: BookmarkService = BookmarkServiceDep,
) -> BookmarkResponse:
    """Добавить закладку."""
    result = await bookmark_service.create_bookmark(user_id, bookmark_data.movie_id)
    return BookmarkResponse(**result)


@router.get(
    "/my",
    response_model=BookmarksListResponse,
    summary="Мои закладки",
    description="Получить список закладок текущего пользователя",
)
@limiter.limit(settings.BOOKMARKS_RATE_LIMIT)
async def get_my_bookmarks(
    request: Request,
    user_id: CurrentUserDep,
    bookmark_service: BookmarkService = BookmarkServiceDep,
) -> BookmarksListResponse:
    """Получить мои закладки."""
    items, total = await bookmark_service.get_user_bookmarks(user_id)

    return BookmarksListResponse(items=items, total=total)



@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить закладку",
    description="Удалить фильм из закладок текущего пользователя",
)
@limiter.limit(settings.BOOKMARKS_RATE_LIMIT)
async def delete_bookmark(
    request: Request,
    user_id: CurrentUserDep,
    movie_id: UUID = Path(..., description="UUID фильма"),
    bookmark_service: BookmarkService = BookmarkServiceDep,
) -> None:
    """Удалить закладку."""
    deleted = await bookmark_service.delete_bookmark(user_id, movie_id)
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Bookmark not found",
        )
