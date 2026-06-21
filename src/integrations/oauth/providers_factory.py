from src.integrations.oauth.base_provider import OAuthBaseProvider
from src.integrations.oauth.google_provider import GoogleOAuthProvider
from src.integrations.oauth.vk_provider import VkOAuthProvider
from src.integrations.oauth.yandex_provider import YandexOAuthProvider
from src.schemas.oauth import AuthProvider


class OAuthProviderFactory:
    def __init__(
        self,
        google: GoogleOAuthProvider,
        yandex: YandexOAuthProvider,
        vk: VkOAuthProvider,
    ):
        self.providers = {
            AuthProvider.GOOGLE: google,
            AuthProvider.YANDEX: yandex,
            AuthProvider.VK: vk,
        }

    def get(self, provider: AuthProvider) -> OAuthBaseProvider:
        return self.providers[provider]
