import secrets

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
