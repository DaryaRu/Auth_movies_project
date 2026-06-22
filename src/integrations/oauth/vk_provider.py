from src.exceptions import ProviderException
from src.integrations.oauth.base_provider import OAuthBaseProvider
from src.schemas.oauth import OAuthUserInfoScheme


class VkOAuthProvider(OAuthBaseProvider):
    def get_auth_url(self, state: str) -> str:
        raise ProviderException(detail="VK провайдер не поддерживается")

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        raise ProviderException(detail="VK провайдер не поддерживается")