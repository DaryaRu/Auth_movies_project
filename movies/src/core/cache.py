import hashlib
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from fastapi import Request, Response


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
