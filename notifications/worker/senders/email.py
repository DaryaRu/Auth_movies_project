"""Email-отправитель через SMTP."""

import asyncio
import time
from email.message import EmailMessage

import aiosmtplib
from core.settings import settings


class CircuitBreakerOpenError(Exception):
    """SMTP считается недоступным — попытка отправки пропущена без реального подключения."""


class EmailSender:
    """Отправка email через SMTP."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_sent_at: float = 0.0
        self._consecutive_failures = 0
        self._circuit_open_until: float | None = None

    async def _throttle_and_check_circuit(self) -> None:
        async with self._lock:
            if (
                self._circuit_open_until is not None
                and time.monotonic() < self._circuit_open_until
            ):
                raise CircuitBreakerOpenError(
                    "SMTP circuit is open, skipping send attempt"
                )

            min_interval = 1 / settings.EMAIL_MAX_PER_SEC
            elapsed = time.monotonic() - self._last_sent_at
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_sent_at = time.monotonic()

    async def _record_result(self, success: bool) -> None:
        async with self._lock:
            if success:
                self._consecutive_failures = 0
                self._circuit_open_until = None
                return

            self._consecutive_failures += 1
            if self._consecutive_failures >= settings.SMTP_FAILURE_THRESHOLD:
                self._circuit_open_until = (
                    time.monotonic() + settings.SMTP_CIRCUIT_COOLDOWN_SEC
                )

    async def send(
        self, delivery_address: str, subject: str | None, body: str
    ) -> None:
        """Собирает и отправляет письмо."""
        await self._throttle_and_check_circuit()

        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = delivery_address
        message["Subject"] = subject or ""
        message.set_content(body)

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_USE_TLS,
            )
        except Exception:
            await self._record_result(False)
            raise
        else:
            await self._record_result(True)
