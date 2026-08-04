import hashlib
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from fastapi import Request, Response


def _normalized_path_query(request: Optional[Request]) -> str:
    url = str(request.url) if request else ""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sorted_query = urlencode(sorted(query.items()))
    return f"{parsed.path}?{sorted_query}"


def key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> str:
    cache_key = hashlib.md5(_normalized_path_query(request).encode()).hexdigest()
    return f"{namespace}:{cache_key}"


def auth_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> str:
    """Дополнительно учитывает уровень доступа пользователя."""
    token_payload = kwargs.get("token_payload") or {}
    if token_payload.get("is_superuser"):
        identity = "superuser"
    else:
        identity = f"level:{token_payload.get('subscription_level', 0)}"
    normalized = f"{_normalized_path_query(request)}:{identity}"
    cache_key = hashlib.md5(normalized.encode()).hexdigest()
    return f"{namespace}:{cache_key}"
