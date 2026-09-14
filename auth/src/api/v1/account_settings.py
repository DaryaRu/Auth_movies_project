"""Изменение данных аккаунта (email, телефон, пароль, таймзона)."""

from fastapi import APIRouter, Request, Response, status

from src.api.v1.dependencies import AccountSettingsServiceDep, CurrentUserDep
from src.core.config import settings
from src.core.limiter import limiter
from src.exceptions import (
    InvalidPhoneChangeCodeException,
    InvalidPhoneChangeCodeHTTPException,
    NoPendingPhoneChangeException,
    NoPendingPhoneChangeHTTPException,
    PasswordAlreadySetException,
    PasswordAlreadySetHTTPException,
    PhoneAlreadyTakenException,
    PhoneAlreadyTakenHTTPException,
    ProviderException,
    ProviderHTTPException,
    SendCooldownException,
    TooManyAttemptsException,
    TooManyAttemptsHTTPException,
    UserAlreadyexistsException,
    UserAlreadyexistsHTTPException,
    UserNotFoundException,
    UserNotFoundHTTPException,
    VerifyPasswordException,
    VerifyPasswordHTTPException,
)
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    ChangeTimezoneRequestScheme,
    PhoneChangeConfirmScheme,
    PhoneChangeRequestScheme,
    SetPasswordRequestScheme,
    UserResponseScheme,
)

router = APIRouter(tags=["Auth"])


@router.patch(
    "/change-email/",
    response_model=UserResponseScheme,
    summary="Смена email",
)
@limiter.limit(settings.LIMIT_VALUE)
async def change_email(
    data: ChangeEmailRequestScheme,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Смена email с подтверждением текущего пароля. Новый email должен быть уникальным."""
    try:
        updated_user = await account_settings_service.change_user_email(
            user_id=user.id, data=data
        )
        return updated_user
    except UserAlreadyexistsException as exc:
        raise UserAlreadyexistsHTTPException(detail=exc.detail) from exc
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc


@router.post(
    "/change-phone-request/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Запрос смены номера телефона",
)
@limiter.limit(settings.LIMIT_VALUE)
async def request_phone_change(
    data: PhoneChangeRequestScheme,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Проверяет пароль и уникальность нового номера, отправляет код
    подтверждения на новый номер. Телефон меняется только после
    /confirm-phone/."""
    try:
        await account_settings_service.request_phone_change(
            user_id=user.id, data=data
        )
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc
    except PhoneAlreadyTakenException as exc:
        raise PhoneAlreadyTakenHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except SendCooldownException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except ProviderException as exc:
        raise ProviderHTTPException(detail=exc.detail) from exc


@router.post(
    "/confirm-phone/",
    response_model=UserResponseScheme,
    summary="Подтверждение смены номера телефона",
)
@limiter.limit(settings.LIMIT_VALUE)
async def confirm_phone_change(
    data: PhoneChangeConfirmScheme,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Проверяет код из СМС, при совпадении обновляет телефон и отзывает
    все сессии (как при смене пароля)."""
    try:
        return await account_settings_service.confirm_phone_change(
            user_id=user.id, data=data
        )
    except InvalidPhoneChangeCodeException as exc:
        raise InvalidPhoneChangeCodeHTTPException(detail=exc.detail) from exc
    except NoPendingPhoneChangeException as exc:
        raise NoPendingPhoneChangeHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc


@router.patch(
    "/change-password/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Смена пароля",
)
@limiter.limit(settings.LIMIT_VALUE)
async def change_password(
    data: ChangePasswordRequestScheme,
    response: Response,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Смена пароля с подтверждением текущего. Сбрасывает все активные сессии."""
    try:
        await account_settings_service.change_user_password(
            user_id=user.id, data=data
        )

        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            path="/",
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc


@router.post(
    "/set-password/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Установка пароля для OAuth-пользователя",
)
async def set_password(
    data: SetPasswordRequestScheme,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
):
    """Устанавливает пароль для пользователя, вошедшего через OAuth (без пароля).
    Если пароль уже установлен — использовать /change-password/.
    """
    try:
        await account_settings_service.set_password(user_id=user.id, data=data)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
    except PasswordAlreadySetException as exc:
        raise PasswordAlreadySetHTTPException(detail=exc.detail) from exc


@router.patch(
    "/users/me/timezone/",
    response_model=UserResponseScheme,
    summary="Смена таймзоны пользователя",
)
@limiter.limit(settings.LIMIT_VALUE)
async def change_user_timezone(
    data: ChangeTimezoneRequestScheme,
    account_settings_service: AccountSettingsServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Смена таймзоны пользователя."""
    try:
        updated_user = await account_settings_service.change_user_timezone(
            user_id=user.id, timezone_name=data.timezone
        )
        return updated_user
    except UserNotFoundException as exc:
        raise UserNotFoundHTTPException(detail=exc.detail) from exc
