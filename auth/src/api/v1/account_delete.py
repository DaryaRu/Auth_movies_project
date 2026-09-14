from fastapi import APIRouter, Request, status

from src.api.v1.dependencies import AuthServiceDep, CurrentUserDep
from src.core.config import settings
from src.core.limiter import limiter
from src.exceptions import (
    AccountDeleteUnavailableException,
    AccountDeleteUnavailableHTTPException,
    InvalidTwoFactorCodeException,
    InvalidTwoFactorCodeHTTPException,
    PasswordNotSetException,
    PasswordNotSetHTTPException,
    ProviderException,
    ProviderHTTPException,
    SendCooldownException,
    TooManyAttemptsException,
    TooManyAttemptsHTTPException,
    VerifyPasswordException,
    VerifyPasswordHTTPException,
)
from src.schemas.tokens import TwoFactorRequiredScheme
from src.schemas.users import (
    AccountDeleteConfirmScheme,
    DeleteAccountRequestScheme,
)

router = APIRouter(tags=["Auth"])


@router.post(
    "/users/me/delete-account-request/",
    response_model=TwoFactorRequiredScheme,
    summary="Запрос на удаление аккаунта",
)
@limiter.limit(settings.LIMIT_VALUE)
async def request_account_delete(
    data: DeleteAccountRequestScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Отправляет код подтверждения в СМС (если указан телефон),
    аккаунт удаляется после подтверждения. Если телефона нет,
    то проверяется текущий пароль и удаляется аккаунт."""
    try:
        two_fa_required = await auth_service.request_account_delete(
            user=user, password=data.password
        )
    except PasswordNotSetException as exc:
        raise PasswordNotSetHTTPException(detail=exc.detail) from exc
    except VerifyPasswordException as exc:
        raise VerifyPasswordHTTPException(detail=exc.detail) from exc
    except AccountDeleteUnavailableException as exc:
        raise AccountDeleteUnavailableHTTPException(
            detail=exc.detail
        ) from exc
    except SendCooldownException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except ProviderException as exc:
        raise ProviderHTTPException(detail=exc.detail) from exc
    return TwoFactorRequiredScheme(two_fa_required=two_fa_required)


@router.post(
    "/users/me/delete-account-confirm/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Подтверждение удаления аккаунта",
)
@limiter.limit(settings.LIMIT_VALUE)
async def confirm_account_delete(
    data: AccountDeleteConfirmScheme,
    auth_service: AuthServiceDep,
    user: CurrentUserDep,
    request: Request,
):
    """Проверяет код из СМС (если у пользователя указан телефоном) и при совпадении удаляет аккаунт."""
    try:
        await auth_service.confirm_account_delete(
            user_id=user.id, code=data.code
        )
    except InvalidTwoFactorCodeException as exc:
        raise InvalidTwoFactorCodeHTTPException(detail=exc.detail) from exc
    except TooManyAttemptsException as exc:
        raise TooManyAttemptsHTTPException(detail=exc.detail) from exc
    except AccountDeleteUnavailableException as exc:
        raise AccountDeleteUnavailableHTTPException(
            detail=exc.detail
        ) from exc
