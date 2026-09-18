"""Удаление аккаунта пользователя (с подтверждением по СМС или паролем)."""

from uuid import UUID

from src.exceptions import (
    AccountDeleteUnavailableException,
    InvalidTwoFactorCodeException,
    PasswordNotSetException,
    VerifyPasswordException,
)
from src.models.users import UserORM
from src.services.sessions import SessionService
from src.services.two_factor import TwoFactorService
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.user_actions import (
    UserActionsUnavailableError,
    delete_user_data,
)


class AccountDeleteService:
    """Удаление аккаунта пользователя (с подтверждением по СМС или паролем)."""

    def __init__(
        self,
        hash_service: BaseHashService,
        db: DBManager,
        session_service: SessionService,
        two_factor_service: TwoFactorService,
    ) -> None:
        self._hash_service = hash_service
        self._db = db
        self._session_service = session_service
        self._two_factor_service = two_factor_service

    async def request_account_delete(
        self, user: UserORM, password: str | None
    ) -> bool:
        """
        Инициирует удаление аккаунта. Если у пользователя указан телефон, то отправляется СМС-код
        для подтверждения, если нет - проверяет текущий пароль и удаляет аккаунт сразу.

        Args:
            user (UserORM): Текущий пользователь.
            password (str | None): Текущий пароль обязателен, если нет телефона.

        Returns:
            bool: True, если отправлен СМС-код и нужен отдельный
                confirm_account_delete. False, если аккаунт уже удален
                (путем проверки пароля).

        Raises:
            PasswordNotSetException: Нет ни телефона, ни пароля для подтверждения.
            VerifyPasswordException: Пароль не указан или неверен.
        """
        if user.phone:
            await self._two_factor_service.send_code(user.id, user.phone)
            return True

        if not user.hashed_password:
            raise PasswordNotSetException()
        if not password or not await self._hash_service.verify_password(
            password, user.hashed_password
        ):
            raise VerifyPasswordException()

        await self._delete_account(user.id)
        return False

    async def confirm_account_delete(self, user_id: UUID, code: str) -> None:
        """
        Подтверждает удаление аккаунта кодом из СМС (для пользователей с телефоном).

        Args:
            user_id (UUID): Идентификатор пользователя.
            code (str): Код подтверждения из СМС.

        Raises:
            InvalidTwoFactorCodeException: Код неверный или истек.
        """
        if not await self._two_factor_service.verify_code(user_id, code):
            raise InvalidTwoFactorCodeException()
        await self._delete_account(user_id)

    async def _delete_account(self, user_id: UUID) -> None:
        """
        Синхронно чистит закладки/оценки/рецензии в user_actions-service,
        затем удаляет пользователя (каскадно удаляются oauth_accounts,
        user_subscriptions, user_notification_settings, user_roles) и
        отзывает все его сессии.

        Если user_actions-service недоступен после ретраев, то ничего не
        удаляется в auth-service. Пользователь может повторить попытку позже.
        """
        try:
            await delete_user_data(user_id)
        except UserActionsUnavailableError as exc:
            raise AccountDeleteUnavailableException() from exc

        await self._db.users.delete_user(user_id)
        await self._session_service.delete_all_sessions(str(user_id))
