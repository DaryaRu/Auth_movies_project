from typing import Any
from uuid import UUID

from src.models.users import UserORM
from src.schemas.users import (
    UpdateFullNameRequestScheme,
    UpdateNicknameRequestScheme,
)
from src.services.base import BaseService
from src.utils.user_activity import get_user_activity


class ProfileService(BaseService):
    """
    Сервис для работы с профилем пользователя.
    Содержит бизнес-логику, не связанную с аутентификацией: чтение и
    редактирование собственных данных профиля.
    """

    async def update_full_name(
        self, user_id: UUID, data: UpdateFullNameRequestScheme
    ) -> UserORM:
        """
        Обновление ФИО пользователя.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (UpdateFullNameRequestScheme): Новые данные профиля.

        Returns:
            UserORM: Обновленный объект пользователя из базы данных.
        """
        return await self._db.users.update_user_credentials(
            user_id=user_id, full_name=data.full_name
        )

    async def update_nickname(
        self, user_id: UUID, data: UpdateNicknameRequestScheme
    ) -> UserORM:
        """
        Обновление никнейма пользователя.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.
            data (UpdateNicknameRequestScheme): Новый никнейм.

        Returns:
            UserORM: Обновленный объект пользователя из базы данных.
        """
        return await self._db.users.update_user_credentials(
            user_id=user_id, nickname=data.nickname
        )

    async def get_user_activity(self, user_id: UUID) -> dict[str, list[Any]]:
        """
        Закладки, оценки и рецензии пользователя из user_actions-service.

        При недоступности user_actions-service возвращает пустые списки.

        Args:
            user_id (UUID): Уникальный идентификатор пользователя.

        Returns:
            dict[str, list[Any]]: {"bookmarks": [...], "likes": [...], "reviews": [...]}.
        """
        return await get_user_activity(user_id)
