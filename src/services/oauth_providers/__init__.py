from src.core.config import settings
from src.services.oauth_providers.base import OAuthUserInfo

PROVIDERS: dict[str, dict] = {}

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    from src.services.oauth_providers.google import google_provider
    PROVIDERS["google"] = google_provider
