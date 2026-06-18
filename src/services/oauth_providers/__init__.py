from src.services.oauth_providers.base import OAuthUserInfo
from src.services.oauth_providers.google import google_provider

PROVIDERS: dict[str, dict] = {
    "google": google_provider,
}
