"""Создание токенов и сессии при входе, определение подписки для JWT."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.models.users import UserORM
from src.services.sessions import SessionService
from src.utils.db_manager import DBManager
from src.utils.tokens import JWTTokenService


class LoginCompletionService:
    """Создает сессию и пару токенов для аутентифицированного пользователя."""

    def __init__(
        self,
        token_service: JWTTokenService,
        session_service: SessionService,
        db: DBManager,
    ) -> None:
        self._token_service = token_service
        self._session_service = session_service
        self._db = db

    async def get_subscription_info(self, user_id: UUID) -> dict:
        """
        Возвращает код и уровень активной подписки пользователя для JWT-токена.
        Если подписка истекла — деактивирует ее и возвращает дефолтные значения 'free'.
        Если активной подписки нет, возвращает дефолтные значения 'free'.

        Args:
            user_id (UUID): Идентификатор пользователя.
        """
        active = await self._db.user_subscriptions.get_active(user_id)
        if active is None:
            return {"subscription_code": "free", "subscription_level": 0}
        if active.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
            timezone.utc
        ):
            await self._db.user_subscriptions.deactivate(active.id)
            return {"subscription_code": "free", "subscription_level": 0}
        return {
            "subscription_code": active.subscription.code,
            "subscription_level": active.subscription.level,
        }

    async def create_session(
        self,
        user: UserORM,
        ip_address: str,
        user_agent: str,
        auth_method: str,
    ) -> tuple[str, str]:
        sid = uuid4()

        subscription_info = await self.get_subscription_info(user.id)

        access_token, refresh_token = (
            self._token_service.create_access_and_refresh_tokens(
                {
                    "sub": str(user.id),
                    "is_superuser": user.is_superuser,
                    "sid": str(sid),
                    **subscription_info,
                }
            )
        )

        await self._session_service.add_session(
            user.id,
            user_agent,
            ip_address,
            refresh_token,
            sid,
            auth_method=auth_method,
        )

        return access_token, refresh_token
