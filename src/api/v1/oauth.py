from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response

from src.api.v1.dependencies import OAuthServiceDep
from src.core.config import settings
from src.exceptions import OAuthStateException, OAuthStateHTTPException, ProviderException, ProviderHTTPException
from src.schemas.oauth import AuthProvider, OAuthURLResponseScheme
from src.schemas.tokens import JWTAccessToken


router = APIRouter(tags=["OAuth"])


@router.get(
    "/auth/{provider}/",
    summary="URL для авторизации на стороне провайдера",
    response_model=OAuthURLResponseScheme
)
async def oauth_redirect(provider: AuthProvider, oauth_service: OAuthServiceDep):
    """Формирует URL авторизации и перенаправляет пользователя на страницу входа провайдера."""
    return {"url": await oauth_service.get_auth_url(provider=provider)}


@router.get(
    "/auth/{provider}/callback/",
    summary="Обработка callback от провайдера",
    response_model=JWTAccessToken,
)
async def oauth_callback(
    provider: AuthProvider,
    code: str,
    state: str,
    request: Request,
    response: Response,
    oauth_service: OAuthServiceDep,
):
    """Получает code от провайдера, выдаёт JWT-токены и устанавливает refresh_token в cookie."""
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    try:
        access_token, refresh_token = await oauth_service.authenticate(
            provider=provider,
            code=code,
            ip_address=ip_address,
            user_agent=user_agent,
            state=state,
        )
    except OAuthStateException as exc:
        raise OAuthStateHTTPException(detail=exc.detail)
    except ProviderException as exc:
        raise ProviderHTTPException(detail=exc.detail)

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
