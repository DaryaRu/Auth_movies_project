"""API endpoints для коротких ссылок."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.repositories.settings import SettingsRepository
from src.schemas.short_links import ShortLinkCreate, ShortLinkResponse
from src.services.short_links import ShortLinkService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["short-links"])

_service = ShortLinkService()
_settings_repo = SettingsRepository()

REDIRECT_URL_KEY = "email_confirmation_redirect_url"


class RedirectUrlResponse(BaseModel):
    """Ответ с текущим redirect_url."""

    redirect_url: str = Field(description="URL для редиректа после подтверждения email")


class RedirectUrlUpdate(BaseModel):
    """Запрос на обновление redirect_url."""

    redirect_url: str = Field(description="URL для редиректа после подтверждения email")


@router.post("/short-links/", response_model=ShortLinkResponse, status_code=201)
async def create_short_link(request: ShortLinkCreate) -> ShortLinkResponse:
    """Создать короткую ссылку для подтверждения email.

    Генерирует уникальный short_key и сохраняет ссылку в БД.
    Возвращает полную короткую ссылку, готовую для вставки в email.
    """
    result = await _service.create_short_link(
        user_id=request.user_id,
        redirect_url=request.redirect_url,
    )
    return result


@router.get("/resolve/{short_key}")
async def redirect_short_link(short_key: str) -> RedirectResponse:
    """Обработать переход по короткой ссылке (HTTP 302 редирект).

    Если ссылка валидна — HTTP 302 на redirect_url.
    Если ссылка просрочена или не найдена — HTTP 404.
    """
    try:
        user_id, redirect_url = await _service.resolve_short_link(short_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ссылка не найдена или просрочена") from None

    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/settings/redirect-url/", response_model=RedirectUrlResponse)
async def get_redirect_url() -> RedirectUrlResponse:
    """Получить текущий redirect_url для подтверждения email."""
    value = await _settings_repo.get(REDIRECT_URL_KEY)
    if value is None:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    return RedirectUrlResponse(redirect_url=value)


@router.put("/settings/redirect-url/", response_model=RedirectUrlResponse)
async def update_redirect_url(request: RedirectUrlUpdate) -> RedirectUrlResponse:
    """Обновить redirect_url для подтверждения email (из админ-панели)."""
    await _settings_repo.set(REDIRECT_URL_KEY, request.redirect_url)
    logger.info("Обновлён redirect_url: %s", request.redirect_url)
    return RedirectUrlResponse(redirect_url=request.redirect_url)
