import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response, status

from src.api.v1.dependencies import OAuthServiceDep
from src.core.config import settings
from src.exceptions import (
    OAuthEmailNotFoundException,
    OAuthEmailNotFoundHTTPException,
    OAuthProviderNotFoundException,
    OAuthProviderNotFoundHTTPException,
)
from src.schemas.oauth_accounts import OAuthRedirectURLScheme
from src.schemas.tokens import JWTAccessToken

router = APIRouter(tags=["OAuth"])


@router.get(
    "/auth/{provider}/",
    summary="URL авторизации провайдера",
    response_model=OAuthRedirectURLScheme,
)
async def oauth_redirect(
    provider: str, response: Response, oauth_service: OAuthServiceDep
):
    """Формирует URL авторизации провайдера и устанавливает cookie с state для CSRF-защиты."""
    try:
        state = secrets.token_urlsafe(16)
        url = oauth_service.get_redirect_url(provider=provider, state=state)
    except OAuthProviderNotFoundException as exc:
        raise OAuthProviderNotFoundHTTPException(detail=exc.detail)

    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        max_age=settings.OAUTH_STATE_EXPIRE_SECONDS,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return OAuthRedirectURLScheme(url=url)


@router.get(
    "/auth/{provider}/callback/",
    summary="Обработка callback от провайдера",
    response_model=JWTAccessToken,
)
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
    oauth_service: OAuthServiceDep,
):
    """Получает code от провайдера, выдаёт JWT-токены и устанавливает refresh_token в cookie."""
    if state != request.cookies.get("oauth_state"):
        raise OAuthProviderNotFoundHTTPException(detail="Невалидный state")

    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    redirect_uri = (
        f"{settings.OAUTH_REDIRECT_BASE_URL}"
        f"{settings.API_V1_PREFIX}/auth/{provider}/callback/"
    )

    try:
        access_token, refresh_token = await oauth_service.authenticate(
            provider=provider,
            code=code,
            redirect_uri=redirect_uri,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except OAuthProviderNotFoundException as exc:
        raise OAuthProviderNotFoundHTTPException(detail=exc.detail)
    except OAuthEmailNotFoundException as exc:
        raise OAuthEmailNotFoundHTTPException(detail=exc.detail)

    response.delete_cookie("oauth_state")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return JWTAccessToken(
        access_token=access_token,
        access_token_expire=datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
