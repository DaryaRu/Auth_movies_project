"""Изменение данных аккаунта (email, телефон, пароль, таймзона)."""

import asyncio
from uuid import UUID

from src.exceptions import (
    InvalidPhoneChangeCodeException,
    PasswordAlreadySetException,
    PasswordNotSetException,
    PhoneAlreadyTakenException,
    UserAlreadyexistsException,
    UserNotFoundException,
    VerifyPasswordException,
)
from src.models.users import UserORM
from src.schemas.users import (
    ChangeEmailRequestScheme,
    ChangePasswordRequestScheme,
    PhoneChangeConfirmScheme,
    PhoneChangeRequestScheme,
    SetPasswordRequestScheme,
)
from src.services.phone_change import PhoneChangeService
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.notifications import notify_user


class AccountSettingsService:
    """Изменение данных аккаунта: email, телефон, пароль, таймзона."""

    def __init__(
        self,
        hash_service: BaseHashService,
        db: DBManager,
        session_service: SessionService,
        phone_change_service: PhoneChangeService,
    ) -> None:
        self._hash_service = hash_service
        self._db = db
        self._session_service = session_service
        self._phone_change_service = phone_change_service

    async def change_user_email(
        self, user_id: UUID, data: ChangeEmailRequestScheme
    ) -> UserORM:
        """
        Смена email пользователя после проверки пароля.
        Проверяет существование пользователя, уникальность нового email
        и корректность текущего пароля.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (ChangeEmailRequestScheme): Данные для смены email.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            UserAlreadyexistsException: Если новый email уже занят.
            PasswordNotSetException: Если у пользователя не задан пароль.
            VerifyPasswordError: Если пароль введен неверно.

        Returns:
            UserORM: Обновленный объект пользователя из базы данных.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        email_exists = await self._db.users.get_one_or_none_by_email(
            data.new_email
        )
        if email_exists:
            raise UserAlreadyexistsException()

        if not user.hashed_password:
            raise PasswordNotSetException()
        if not self._hash_service.verify_password(
            data.password, user.hashed_password
        ):
            raise VerifyPasswordException()

        updated_user = await self._db.users.update_user_credentials(
            user_id=user_id, email=data.new_email
        )
        return updated_user

    async def request_phone_change(
        self, user_id: UUID, data: PhoneChangeRequestScheme
    ) -> None:
        """
        Запрашивает смену телефона: проверяет пароль и уникальность нового
        номера, отправляет два независимых кода подтверждения: на новый
        номер (СМС) и на текущий email аккаунта.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (PhoneChangeRequestScheme): Новый номер и текущий пароль.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            PasswordNotSetException: Если у пользователя не задан пароль.
            VerifyPasswordException: Если пароль введен неверно.
            PhoneAlreadyTakenException: Если номер уже занят другим аккаунтом.
            EmailRequiredForPhoneChangeException: На аккаунте нет email.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if user is None:
            raise UserNotFoundException()

        if not user.hashed_password:
            raise PasswordNotSetException()
        if not self._hash_service.verify_password(
            data.password, user.hashed_password
        ):
            raise VerifyPasswordException()

        phone_taken = await self._db.users.get_one_or_none_by_email_or_phone(
            email=None, phone=data.new_phone
        )
        if phone_taken is not None:
            raise PhoneAlreadyTakenException()

        await self._phone_change_service.request_change(
            user_id, data.new_phone, user.email
        )

    async def confirm_phone_change(
        self, user_id: UUID, data: PhoneChangeConfirmScheme
    ) -> UserORM:
        """
        Подтверждает смену телефона двумя кодами (СМС + email): обновляет
        телефон, отзывает все сессии и уведомляет на email.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (PhoneChangeConfirmScheme): Коды подтверждения из СМС и email.
        """
        new_phone = await self._phone_change_service.confirm_change(
            user_id, data.sms_code, data.email_code
        )
        if new_phone is None:
            raise InvalidPhoneChangeCodeException()

        updated_user = await self._db.users.update_user_credentials(
            user_id=user_id, phone=new_phone
        )
        await self._session_service.delete_all_sessions(str(user_id))
        asyncio.create_task(notify_user(user_id, "phone_changed"))
        return updated_user

    async def change_user_password(
        self, user_id: UUID, data: ChangePasswordRequestScheme
    ) -> None:
        """
        Смена пароля пользователя и отзыв всех его текущих сессий.
        Проверяет существование пользователя, корректность старого пароля,
        после чего хэширует новый пароль и удаляет все токены.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (ChangePasswordRequestScheme): Данные для смены пароля.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            PasswordNotSetException: Если у пользователя не задан пароль.
            VerifyPasswordException: Если текущий старый пароль введен неверно.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        if not user.hashed_password:
            raise PasswordNotSetException()
        if not self._hash_service.verify_password(
            data.current_password, user.hashed_password
        ):
            raise VerifyPasswordException()

        new_hash = self._hash_service.create_hash_password(data.new_password)

        await self._db.users.update_user_credentials(
            user_id=user_id, hashed_password=new_hash
        )

        await self._session_service.delete_all_sessions(str(user_id))
        asyncio.create_task(notify_user(user_id, "password_changed"))

    async def change_user_timezone(
        self, user_id: UUID, timezone_name: str
    ) -> UserORM:
        """
        Смена таймзоны пользователя.
        Применяется только к будущим рассылкам.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            timezone_name (str): IANA-имя новой таймзоны.

        Raises:
            UserNotFoundException: Если пользователь не найден.

        Returns:
            UserORM: Обновленный объект пользователя.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        await self._db.users.update_user_timezone(
            user_id=user_id, timezone=timezone_name
        )

        return user

    async def set_password(
        self, user_id: UUID, data: SetPasswordRequestScheme
    ) -> None:
        """Устанавливает пароль для OAuth-пользователя без пароля.

        Raises:
            UserNotFoundException: Если пользователь не найден.
            PasswordAlreadySetException: Если пароль уже установлен (использовать change-password).
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if not user:
            raise UserNotFoundException()

        if user.hashed_password is not None:
            raise PasswordAlreadySetException()

        new_hash = self._hash_service.create_hash_password(data.password)
        await self._db.users.update_user_credentials(
            user_id=user_id,
            hashed_password=new_hash,
        )
