
import hashlib

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response

from src.core.config import settings


def get_combined_key(request: Request) -> str:
    """Комбинация IP + User-Agent"""
    
    real_ip = get_remote_address(request)
    user_agent = request.headers.get("User-Agent", "unknown")

    combined = f"{real_ip}:{user_agent}"
    return hashlib.md5(combined.encode()).hexdigest()


limiter = Limiter(
    key_func=get_combined_key,
    storage_uri=settings.REDIS_LIMITER_URL,
    default_limits=[f"{settings.DEFAULT_LIMIT_VALUE}/minute"],
)


async def rate_limit_exceeded_handler(
        request: Request, exc: RateLimitExceeded
        ):
    return Response(
        content='{"detail":"Too Many Requests. Please try again later."}',
        status_code=429,
        media_type="application/json"
    )
