from enum import Enum

from pydantic import BaseModel, EmailStr


class AuthProvider(str, Enum):
    GOOGLE = "google"
    YANDEX = "yandex"
    VK = "vk"
    
    
class OAuthUserInfoScheme(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    provider: AuthProvider
    provider_user_id: str


class OAuthURLResponseScheme(BaseModel):
    url: str
