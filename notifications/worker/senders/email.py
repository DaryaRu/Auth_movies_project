"""Email-отправитель через SMTP."""

import asyncio
import time
from email.message import EmailMessage

import aiosmtplib
from core.settings import settings


class EmailSender:
    """Отправка email через SMTP. Ограничивает скорость отправки
    (EMAIL_MAX_PER_SEC), чтобы не перегружать SMTP-сервер при массовой рассылке."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_sent_at: float = 0.0

    async def _throttle(self) -> None:
        min_interval = 1 / settings.EMAIL_MAX_PER_SEC
        async with self._lock:
            elapsed = time.monotonic() - self._last_sent_at
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_sent_at = time.monotonic()

    async def send(
        self, delivery_address: str, subject: str | None, body: str
    ) -> None:
        """Собирает и отправляет письмо. Бросает исключение при сбое SMTP."""
        await self._throttle()

        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = delivery_address
        message["Subject"] = subject or ""
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
        )
