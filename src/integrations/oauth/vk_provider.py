from src.integrations.oauth.base_provider import OAuthProvider
from src.schemas.oauth import OAuthUserInfoScheme


class VkOAuthProvider(OAuthProvider):
    async def get_auth_url(self, state: str) -> str:
        ...

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        ...