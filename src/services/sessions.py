import hashlib
from typing import Any
from uuid import UUID

from src.exceptions import TokenExeption
from src.repositories.sessions import SessionAbstractRepository


class SessionService:
    def __init__(self, repo: SessionAbstractRepository) -> None:
        self._repo = repo
        
    @staticmethod
    def _get_refresh_token_hash(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()
        
    async def add_session(self, user_id: UUID, ip: str, user_agent: str, refresh_token: str, sid: UUID) -> None:
        refresh_hash = self._get_refresh_token_hash(refresh_token)
        await self._repo.delete_session_by_device(str(user_id), ip, user_agent)
        await self._repo.add_user_session(
            user_id=str(user_id),
            user_agent=user_agent,
            ip=ip,
            refresh_token_hash=refresh_hash,
            sid=str(sid),
        )
        
    async def get_session(self, sid: str) -> dict[str, Any] | None:
        return await self._repo.get_user_session(sid)
        
    async def verify_session(self, sid: str, refresh_token: str) -> None:
        session = await self.get_session(sid)
        if session is None:
            raise TokenExeption()
        refresh_hash = self._get_refresh_token_hash(refresh_token)
        if session["refresh_token_hash"] != refresh_hash:
            raise TokenExeption()

    async def rotate_refresh_token(self, sid: str, refresh_token: str) -> None:
        refresh_hash = self._get_refresh_token_hash(refresh_token)
        await self._repo.update_refresh_token_hash(
            sid=sid,
            refresh_token_hash=refresh_hash,
        )

    async def delete_session(self, sid: str) -> None:
        await self._repo.delete_user_session(sid)
        
    async def delete_all_sessions(self, user_id: str) -> None:
        await self._repo.delete_all_user_session(user_id)
        
    async def get_active_sessions(self, user_id: UUID, current_sid: str) -> list[dict]:
        return await self._repo.get_user_sessions(user_id, str(current_sid))
