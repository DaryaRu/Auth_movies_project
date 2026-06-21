import asyncio
import logging
import secrets
from uuid import UUID

from redis.asyncio import Redis

from src.core.config import settings
from src.exceptions import OAuthStateException
from src.integrations.oauth.providers_factory import OAuthProviderFactory
from src.schemas.oauth import AuthProvider
from src.services.auth import AuthService


class OAuthService:
    def __init__(self, provider_factory: OAuthProviderFactory, auth_service: AuthService, redis: Redis) -> None:
        self._provider_factory = provider_factory
        self._auth_service = auth_service
        self._redis = redis
        
    async def get_auth_url(self, provider: AuthProvider) -> str:
        state = secrets.token_urlsafe(16)
        await self._redis.setex(
            f"oauth_state:{state}",
            settings.OAUTH_STATE_EXPIRE_SECONDS,
            provider.value
        )
        strategy = self._provider_factory.get(provider)
        return strategy.get_auth_url(state)
    
    async def authenticate(
        self,
        provider: AuthProvider,
        code: str,
        ip_address: str,
        user_agent: str,
        state: str,
    ) -> tuple[str, str]:
        stored_provider_key = f"oauth_state:{state}"
        stored_provider = await self._redis.get(stored_provider_key)
        if not stored_provider or stored_provider != provider.value:
            raise OAuthStateException()
        await self._redis.delete(stored_provider_key)
        strategy = self._provider_factory.get(provider)
        oauth_user = await strategy.get_user_info(code)
        return await self._auth_service.authenticate_oauth_user(
            oauth_user,
            ip_address,
            user_agent,
        )

    async def unlink_account(
            self,
            user_id: UUID,
            provider_str: str,
            current_sid: str
        ) -> tuple[list[str], bool]:
        """
        Координирует отвязку аккаунта.
        1. Вызывает AuthService для удаления данных и получения токена
        2. Отзывает токен в фоне (если есть)

        Returns:
            tuple[list[str], bool]: (оставшиеся_провайдеры, удалена_ли_текущая_сессия)
        """
        try:
            provider_enum = AuthProvider(provider_str)
        except ValueError:
            logging.error(f"Неизвестный провайдер для отвязки: {provider_str}")
            return [], False

        remaining_providers, access_token, current_session_deleted = await self._auth_service.unlink_account(
            user_id=user_id,
            provider=provider_str,
            current_sid=current_sid
        )

        if access_token:
            try:
                strategy = self._provider_factory.get(provider_enum)
                if hasattr(strategy, "revoke_token"):
                    asyncio.create_task(self._revoke_token_safely(
                        strategy,
                        access_token,
                        provider_str
                        )
                    )
                    logging.info(f"Запущен отзыв токена для {provider_str}")
            except Exception as e:
                logging.error(f"Не удалось запустить"
                              f"отзыв токена для {provider_str}: {e}")

        return remaining_providers, current_session_deleted

    async def _revoke_token_safely(
            self,
            strategy,
            access_token: str,
            provider_str: str,
    ):
        """Безопасно отзывает токен с логированием ошибок."""
        try:
            await strategy.revoke_token(access_token)
            logging.info(f"Токен для {provider_str} успешно отозван")
        except Exception as e:
            logging.error(f"Ошибка при отзыве токена для {provider_str}: {e}")
