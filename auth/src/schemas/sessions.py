from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserSessionResponse(BaseModel):
    sid: UUID
    ip: str | None
    user_agent: str | None
    is_current: bool
    created_at: datetime | None


class SessionInfoScheme(BaseModel):
    """Схема подтверждения активности сессии для внутренних вызовов."""

    sid: str
    user_id: UUID
