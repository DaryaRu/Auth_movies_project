from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from src.core.config import settings


class SessionAbstractRepository(ABC):
    @abstractmethod
    async def add_user_session(
        self,
        user_id: str,
        ip: str,
        user_agent: str,
        refresh_token_hash: str,
        sid: str,
        auth_method: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_user_session(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError
    
    @abstractmethod
    async def update_refresh_token_hash(self, sid: str, refresh_token_hash: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def delete_user_session(self, sid: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def delete_all_user_session(self, user_id: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_user_sessions(
        self,
        user_id: str,
        current_sid: str
    ) -> list[dict]:
        raise NotImplementedError
    
    @abstractmethod
    async def delete_session_by_device(
        self,
        user_id: str,
        ip: str,
        user_agent: str,
    ) -> None:
        raise NotImplementedError
    
    
class SessionRedisRepository(SessionAbstractRepository):
    def __init__(self, redis: Redis):
        self._redis = redis
        
    async def add_user_session(
            self,
            user_id: str,
            ip: str,
            user_agent: str,
            refresh_token_hash: str,
            sid: str,
            auth_method: str,
    ) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            key = f"session:{sid}"
            ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            pipe.hset(
                key,
                mapping={
                    "user_id": user_id,
                    "ip": ip,
                    "user_agent": user_agent,
                    "refresh_token_hash": refresh_token_hash,
                    "auth_method": auth_method,
                    "created_at": datetime.now(UTC).isoformat()
                }
            )
            pipe.expire(key, ttl)
            pipe.sadd(
                f"user_sessions:{user_id}",
                sid,
            )
            await pipe.execute()
    
    async def update_refresh_token_hash(
        self,
        sid: str,
        refresh_token_hash: str
    ) -> None:
        key = f"session:{sid}"
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, "refresh_token_hash", refresh_token_hash)
            pipe.expire(key, ttl)
            await pipe.execute()
        
    async def get_user_session(self, sid: str) -> dict[str, Any]:
        key = f"session:{sid}"
        session = await self._redis.hgetall(key)
        return session
        
    async def delete_user_session(self, sid: str) -> None:
        key = f"session:{sid}"
        session = await self.get_user_session(sid)
        if not session:
            return
        user_id = session.get("user_id")
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)

            if user_id:
                pipe.srem(f"user_sessions:{user_id}", sid)

            await pipe.execute()
            
    async def delete_all_user_session(self, user_id: str) -> None:
        user_sessions_key = f"user_sessions:{user_id}"
        sids = await self._redis.smembers(user_sessions_key)
        if not sids:
            return
        async with self._redis.pipeline(transaction=True) as pipe:
            for sid in sids:
                pipe.delete(f"session:{sid}")
            pipe.delete(user_sessions_key)
            await pipe.execute()
            
    async def get_user_sessions(
        self,
        user_id: str,
        current_sid: str
    ) -> list[dict]:
        sids = await self._redis.smembers(f"user_sessions:{user_id}")
        if not sids:
            return []
        result = []
        async with self._redis.pipeline(transaction=False) as pipe:
            for sid in sids:
                pipe.hgetall(f"session:{sid}")
            sessions = await pipe.execute()
        for sid, session in zip(sids, sessions):
            if not session:
                continue
            result.append({
                "sid": sid,
                "ip": session.get("ip"),
                "user_agent": session.get("user_agent"),
                "is_current": sid == current_sid,
                "created_at": datetime.fromisoformat(session.get("created_at")),
            })

        return result
    
    async def delete_session_by_device(
        self,
        user_id: str,
        ip: str,
        user_agent: str,
    ) -> None:
        sids = await self._redis.smembers(f"user_sessions:{user_id}")
        if not sids:
            return

        async with self._redis.pipeline(transaction=False) as pipe:
            for sid in sids:
                pipe.hgetall(f"session:{sid}")
            sessions = await pipe.execute()

        for sid, session in zip(sids, sessions):
            if not session:
                continue
            if session.get("ip") == ip and session.get("user_agent") == user_agent:
                await self.delete_user_session(sid)
