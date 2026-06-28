from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query, Request, Response

from src.api.v1.dependencies import OAuthServiceDep, CurrentUserDep, TokenPayloadDep

from src.core.config import settings
from src.exceptions import (
    OAuthStateException,
    OAuthStateHTTPException,
    ProviderException,
    ProviderHTTPException,
    UserNotFoundException,
    UserNotFoundHTTPException,
    OAuthAccountNotLinkedException,
    OAuthAccountNotLinkedHTTPException,
    LastAuthMethodRestrictionException,
    LastAuthMethodRestrictionHTTPException,
)
from src.schemas.oauth import (
    AuthProvider,
    OAuthURLResponseScheme,
)
from src.schemas.oauth_accounts import OAuthUnlinkResponseScheme
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
    device_id: Optional[str] = Query(None),
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
            device_id=device_id,
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


@router.delete(
    "/auth/{provider}/unlink/",
    summary="Отвязать аккаунт социальной сети",
    response_model=OAuthUnlinkResponseScheme,
)
async def oauth_unlink(
    provider: AuthProvider,
    response: Response,
    oauth_service: OAuthServiceDep,
    current_user: CurrentUserDep,
    token_payload: TokenPayloadDep,
):
    current_sid = token_payload["sid"]

    try:
        remaining_providers, current_session_deleted = await oauth_service.unlink_account(
            user_id=current_user.id,
            provider_str=provider.value,
            current_sid=current_sid
        )
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail)
    except OAuthAccountNotLinkedException as exc:
        raise OAuthAccountNotLinkedHTTPException(detail=exc.detail)
    except LastAuthMethodRestrictionException as exc:
        raise LastAuthMethodRestrictionHTTPException(detail=exc.detail)

    if current_session_deleted:
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            path="/",
        )

    return OAuthUnlinkResponseScheme(
        message=f"Аккаунт {provider.capitalize()} успешно отвязан.",
        linked_providers=remaining_providers,
    )
