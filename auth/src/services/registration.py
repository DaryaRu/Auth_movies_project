"""Регистрация пользователя, подтверждение email, создание суперпользователя."""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from src.exceptions import UserAlreadyexistsException, UserNotFoundException
from src.models.users import UserORM
from src.schemas.users import UserRequestScheme
from src.utils.db_manager import DBManager
from src.utils.hashes import BaseHashService
from src.utils.notifications import notify_user
from src.utils.short_links import create_short_link


class RegistrationService:
    """Регистрация пользователя, подтверждение email, создание суперпользователя."""

    def __init__(self, hash_service: BaseHashService, db: DBManager) -> None:
        self._hash_service = hash_service
        self._db = db

    async def register_user(self, user: UserRequestScheme) -> UserORM:
        is_exsist_user = (
            await self._db.users.get_one_or_none_by_email_or_phone(
                user.email, user.phone
            )
        )
        if is_exsist_user:
            raise UserAlreadyexistsException()
        new_user = await self.add_one(user)

        asyncio.create_task(self._send_confirmation_email(new_user.id))
        return new_user

    async def _send_confirmation_email(self, user_id: UUID) -> None:
        """Асинхронная отправка письма с подтверждением email."""
        try:
            confirmation_link = await create_short_link(user_id=user_id)
        except Exception as e:
            logging.warning(
                "Failed to create confirmation link for user %s: %s",
                user_id,
                e,
            )
            return
        await notify_user(
            user_id,
            "user_registered",
            payload={"confirmation_link": confirmation_link},
        )

    async def confirm_email(self, user_id: UUID) -> UserORM:
        """Подтверждает email пользователя по user_id из короткой ссылки.

        Args:
            user_id: Идентификатор пользователя.

        Returns:
            UserORM: Обновленный объект пользователя.

        Raises:
            UserNotFoundException: Если пользователь не найден.
        """
        user = await self._db.users.get_one_or_none_by_id(id=user_id)
        if user is None:
            raise UserNotFoundException()

        updated_user = await self._db.users.update_user_credentials(
            user_id=user_id,
            email_verified=True,
        )
        return updated_user

    async def create_admin(self, user: UserRequestScheme) -> None:
        is_exsist_user = (
            await self._db.users.get_one_or_none_by_email_or_phone(
                user.email, user.phone
            )
        )
        if is_exsist_user:
            raise UserAlreadyexistsException()
        await self.add_one(user, is_superuser=True)

    async def add_one(
        self, user: UserRequestScheme, is_superuser: bool = False
    ) -> UserORM:
        """
        Добавляет нового пользователя.
        - Пароль пользователя хэшируется.
        - Оригинальный пароль удаляется перед сохранением.
        - Пользователь сохраняется в БД.
        - Пользователю назначается базовая подписка 'free'.
        Args:
            user (UserRequestScheme): Данные пользователя.
        Returns:
            UserORM: Пользователь.
        """
        hash_password = await self._hash_service.create_hash_password(
            user.password
        )
        new_user = await self._db.users.create_user(
            phone=user.phone,
            email=user.email,
            hashed_password=hash_password,
            is_superuser=is_superuser,
            timezone=user.timezone,
            full_name=user.full_name,
        )
        await self.assign_free_subscription(new_user.id)
        return new_user

    async def assign_free_subscription(self, user_id: UUID) -> None:
        free_sub = await self._db.subscriptions.get_one_or_none_by_code("free")
        if free_sub is None:
            logging.warning(
                "Подписка 'free' не найдена в БД, не удается назначить"
            )
            return
        await self._db.user_subscriptions.create(
            user_id=user_id,
            subscription_id=free_sub.id,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime(2999, 12, 31, tzinfo=timezone.utc),
        )
