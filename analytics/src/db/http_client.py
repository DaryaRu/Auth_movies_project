"""HTTP-клиент."""

from typing import Optional

import httpx

client: Optional[httpx.AsyncClient] = None
