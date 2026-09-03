from uuid import UUID

from src.models.users import UserORM
from src.schemas.users import UpdateFullNameRequestScheme
from src.services.base import BaseService


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
