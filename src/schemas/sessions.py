from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class UserSessionResponse(BaseModel):
    sid: UUID
    ip: str | None
    user_agent: str | None
    is_current: bool
    created_at: datetime | None
