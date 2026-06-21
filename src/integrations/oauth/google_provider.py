from src.integrations.oauth.base_provider import OAuthBaseProvider
from src.schemas.oauth import OAuthUserInfoScheme


class GoogleOAuthProvider(OAuthBaseProvider):
    async def get_auth_url(self, state: str) -> str:
        ...

    async def get_user_info(self, code: str) -> OAuthUserInfoScheme:
        ...
