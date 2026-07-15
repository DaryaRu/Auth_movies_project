import hashlib
import logging
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from fastapi import Request, Response
from fastapi_cache import FastAPICache
from redis.asyncio import Redis

from src.core.config import settings
from src.db import redis
from src.db.redis import FaultTolerantRedisBackend


def key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> str:
    url = str(request.url) if request else ""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sorted_query = urlencode(sorted(query.items()))
    normalized = f"{parsed.path}?{sorted_query}"
    cache_key = hashlib.md5(normalized.encode()).hexdigest()
    return f"{namespace}:{cache_key}"


async def init_cache() -> None:
    redis.redis = Redis.from_url(settings.REDIS_URL)
    FastAPICache.init(
        FaultTolerantRedisBackend(redis.redis),
        prefix="fastapi-cache",
        key_builder=key_builder,
    )
    logging.info("FastAPI cache initialized")


async def close_cache() -> None:
    if redis.redis is not None:
        await redis.redis.aclose()
